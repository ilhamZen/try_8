import { Injectable } from '@nestjs/common';
import { db } from '../../../db/connection';
import { wallets, transactions } from '../../../db/schema';
import { eq } from 'drizzle-orm';

export interface TransactionResult {
  success: boolean;
  balanceBefore: number;
  balanceAfter: number;
  transactionId: string;
}

@Injectable()
export class EconomyService {
  /**
   * Get wallet balance for account
   */
  async getBalance(accountId: string): Promise<{ wallet: number; bank: number }> {
    const [wallet] = await db.select().from(wallets).where(
      eq(wallets.accountId, accountId)
    ).limit(1);

    if (!wallet) {
      // Create default wallet
      const now = new Date().toISOString();
      await db.insert(wallets).values({
        id: crypto.randomUUID(),
        accountId,
        balance: 0,
        bankBalance: 0,
        updatedAt: now,
      });
      return { wallet: 0, bank: 0 };
    }

    return {
      wallet: wallet.balance,
      bank: wallet.bankBalance,
    };
  }

  /**
   * Add money to wallet with transaction log
   */
  async credit(
    accountId: string, 
    amount: number, 
    source: string, 
    reference?: string
  ): Promise<TransactionResult> {
    const now = new Date().toISOString();
    const txId = crypto.randomUUID();

    const [wallet] = await db.select().from(wallets).where(
      eq(wallets.accountId, accountId)
    ).limit(1);

    if (!wallet) {
      throw new Error('Wallet not found');
    }

    const balanceBefore = wallet.balance;
    const balanceAfter = balanceBefore + amount;

    await db.transaction(async (tx) => {
      // Update wallet
      await tx.update(wallets)
        .set({
          balance: balanceAfter,
          updatedAt: now,
        })
        .where(eq(wallets.id, wallet.id));

      // Log transaction
      await tx.insert(transactions).values({
        id: txId,
        accountId,
        type: 'credit',
        amount,
        balanceBefore,
        balanceAfter,
        source,
        reference: reference || null,
        createdAt: now,
      });
    });

    return {
      success: true,
      balanceBefore,
      balanceAfter,
      transactionId: txId,
    };
  }

  /**
   * Remove money from wallet with transaction log
   */
  async debit(
    accountId: string, 
    amount: number, 
    source: string, 
    reference?: string
  ): Promise<TransactionResult> {
    const now = new Date().toISOString();
    const txId = crypto.randomUUID();

    const [wallet] = await db.select().from(wallets).where(
      eq(wallets.accountId, accountId)
    ).limit(1);

    if (!wallet) {
      throw new Error('Wallet not found');
    }

    if (wallet.balance < amount) {
      throw new Error('Insufficient funds');
    }

    const balanceBefore = wallet.balance;
    const balanceAfter = balanceBefore - amount;

    await db.transaction(async (tx) => {
      // Update wallet
      await tx.update(wallets)
        .set({
          balance: balanceAfter,
          updatedAt: now,
        })
        .where(eq(wallets.id, wallet.id));

      // Log transaction
      await tx.insert(transactions).values({
        id: txId,
        accountId,
        type: 'debit',
        amount,
        balanceBefore,
        balanceAfter,
        source,
        reference: reference || null,
        createdAt: now,
      });
    });

    return {
      success: true,
      balanceBefore,
      balanceAfter,
      transactionId: txId,
    };
  }

  /**
   * Transfer money between accounts
   */
  async transfer(
    fromAccountId: string,
    toAccountId: string,
    amount: number,
    source: string,
    reference?: string
  ): Promise<{ from: TransactionResult; to: TransactionResult }> {
    const now = new Date().toISOString();

    // Debit from sender
    const fromResult = await this.debit(fromAccountId, amount, source, reference);

    try {
      // Credit to receiver
      const toResult = await this.credit(toAccountId, amount, source, reference);
      return { from: fromResult, to: toResult };
    } catch (error) {
      // Rollback sender transaction
      await this.credit(fromAccountId, amount, `${source}_rollback`, reference);
      throw error;
    }
  }

  /**
   * Deposit to bank
   */
  async depositToBank(accountId: string, amount: number): Promise<TransactionResult> {
    const now = new Date().toISOString();
    const txId = crypto.randomUUID();

    const [wallet] = await db.select().from(wallets).where(
      eq(wallets.accountId, accountId)
    ).limit(1);

    if (!wallet) {
      throw new Error('Wallet not found');
    }

    if (wallet.balance < amount) {
      throw new Error('Insufficient funds');
    }

    const balanceBefore = wallet.balance;
    const balanceAfter = balanceBefore - amount;
    const bankBalanceAfter = wallet.bankBalance + amount;

    await db.update(wallets)
      .set({
        balance: balanceAfter,
        bankBalance: bankBalanceAfter,
        updatedAt: now,
      })
      .where(eq(wallets.id, wallet.id));

    return {
      success: true,
      balanceBefore,
      balanceAfter,
      transactionId: txId,
    };
  }

  /**
   * Withdraw from bank
   */
  async withdrawFromBank(accountId: string, amount: number): Promise<TransactionResult> {
    const now = new Date().toISOString();
    const txId = crypto.randomUUID();

    const [wallet] = await db.select().from(wallets).where(
      eq(wallets.accountId, accountId)
    ).limit(1);

    if (!wallet) {
      throw new Error('Wallet not found');
    }

    if (wallet.bankBalance < amount) {
      throw new Error('Insufficient bank funds');
    }

    const balanceBefore = wallet.balance;
    const balanceAfter = balanceBefore + amount;
    const bankBalanceAfter = wallet.bankBalance - amount;

    await db.update(wallets)
      .set({
        balance: balanceAfter,
        bankBalance: bankBalanceAfter,
        updatedAt: now,
      })
      .where(eq(wallets.id, wallet.id));

    return {
      success: true,
      balanceBefore,
      balanceAfter,
      transactionId: txId,
    };
  }

  /**
   * Get transaction history
   */
  async getTransactionHistory(accountId: string, limit: number = 20) {
    const txs = await db.select().from(transactions).where(
      eq(transactions.accountId, accountId)
    )
    .orderBy((t) => t.createdAt DESC)
    .limit(limit);

    return txs;
  }
}
