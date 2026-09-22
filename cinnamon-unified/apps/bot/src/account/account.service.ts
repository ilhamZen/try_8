import { Injectable, Logger } from '@nestjs/common';
import { v4 as uuidv4 } from 'uuid';
import * as argon2 from 'argon2';
import { getDatabase } from '@db/connection';
import { accounts, identities, profiles, wallets, recoveryCodes } from '@db/schema';
import { eq } from 'drizzle-orm';

export interface RegisterDto {
  password: string;
  displayName?: string;
}

export interface LoginDto {
  accountId: string;
  password: string;
}

export interface RecoverDto {
  accountId: string;
  recoveryCode: string;
  newIdentity?: {
    type: string;
    identifier: string;
  };
}

@Injectable()
export class AccountService {
  private readonly logger = new Logger(AccountService.name);

  /**
   * Register akun baru dengan UUID permanent
   */
  async register(dto: RegisterDto): Promise<{ accountId: string; recoveryCodes: string[] }> {
    const db = getDatabase();
    
    const accountId = uuidv4();
    const passwordHash = await argon2.hash(dto.password);
    const now = new Date().toISOString();

    // Generate 10 recovery codes
    const rawRecoveryCodes = this.generateRecoveryCodes(10);
    const hashedCodes = await Promise.all(
      rawRecoveryCodes.map(code => argon2.hash(code))
    );

    try {
      // Transaction untuk membuat account + profile + wallet + recovery codes
      await db.transaction(async (tx) => {
        // Create account
        await tx.insert(accounts).values({
          id: accountId,
          passwordHash,
          createdAt: now,
          updatedAt: now,
          status: 'active',
        });

        // Create profile
        await tx.insert(profiles).values({
          id: uuidv4(),
          accountId,
          displayName: dto.displayName || null,
          rank: 'user',
          level: 1,
          xp: 0,
          reputation: 0,
          createdAt: now,
          updatedAt: now,
        });

        // Create wallet
        await tx.insert(wallets).values({
          id: uuidv4(),
          accountId,
          balance: 0,
          bankBalance: 0,
          updatedAt: now,
        });

        // Insert recovery codes
        for (let i = 0; i < rawRecoveryCodes.length; i++) {
          await tx.insert(recoveryCodes).values({
            id: uuidv4(),
            accountId,
            codeHash: hashedCodes[i],
            used: false,
            createdAt: now,
          });
        }
      });

      this.logger.log(`✅ Account registered: ${accountId}`);
      
      return {
        accountId,
        recoveryCodes: rawRecoveryCodes,
      };
    } catch (error: any) {
      this.logger.error(`❌ Registration failed: ${error.message}`);
      throw error;
    }
  }

  /**
   * Login dengan accountId + password
   */
  async login(dto: LoginDto): Promise<{ accountId: string; valid: boolean }> {
    const db = getDatabase();

    const account = await db.query.accounts.findFirst({
      where: eq(accounts.id, dto.accountId),
    });

    if (!account) {
      this.logger.warn(`⚠️ Login failed: Account not found`);
      return { accountId: dto.accountId, valid: false };
    }

    const isValid = await argon2.verify(account.passwordHash, dto.password);

    if (!isValid) {
      this.logger.warn(`⚠️ Login failed: Invalid password`);
      return { accountId: dto.accountId, valid: false };
    }

    // Update last login
    await db.update(accounts)
      .set({ 
        lastLoginAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      })
      .where(eq(accounts.id, dto.accountId));

    this.logger.log(`✅ Login successful: ${dto.accountId}`);

    return {
      accountId: dto.accountId,
      valid: true,
    };
  }

  /**
   * Recover account dengan recovery code
   */
  async recover(dto: RecoverDto): Promise<{ success: boolean; message: string }> {
    const db = getDatabase();

    // Verify account exists
    const account = await db.query.accounts.findFirst({
      where: eq(accounts.id, dto.accountId),
    });

    if (!account) {
      return { success: false, message: 'Account not found' };
    }

    // Find unused recovery code
    const codeRecord = await db.query.recoveryCodes.findFirst({
      where: eq(recoveryCodes.accountId, dto.accountId),
    });

    if (!codeRecord || codeRecord.used) {
      return { success: false, message: 'Invalid or used recovery code' };
    }

    // Verify recovery code
    const isValid = await argon2.verify(codeRecord.codeHash, dto.recoveryCode);
    if (!isValid) {
      return { success: false, message: 'Invalid recovery code' };
    }

    try {
      await db.transaction(async (tx) => {
        // Mark code as used
        await tx.update(recoveryCodes)
          .set({ 
            used: true,
            usedAt: new Date().toISOString(),
          })
          .where(eq(recoveryCodes.id, codeRecord.id));

        // Link new identity if provided
        if (dto.newIdentity) {
          await tx.insert(identities).values({
            id: uuidv4(),
            accountId: dto.accountId,
            type: dto.newIdentity.type,
            identifier: dto.newIdentity.identifier,
            isPrimary: false,
            linkedAt: new Date().toISOString(),
            verifiedAt: new Date().toISOString(),
          });
        }
      });

      this.logger.log(`✅ Account recovered: ${dto.accountId}`);
      return { success: true, message: 'Account recovered successfully' };
    } catch (error: any) {
      this.logger.error(`❌ Recovery failed: ${error.message}`);
      return { success: false, message: 'Recovery failed' };
    }
  }

  /**
   * Get account by ID
   */
  async getAccount(accountId: string) {
    const db = getDatabase();
    
    const account = await db.query.accounts.findFirst({
      where: eq(accounts.id, accountId),
      with: {
        identities: true,
        profile: true,
        wallet: true,
      },
    });

    return account || null;
  }

  /**
   * Link identity ke account
   */
  async linkIdentity(accountId: string, type: string, identifier: string): Promise<void> {
    const db = getDatabase();

    // Check if identity already exists
    const existing = await db.query.identities.findFirst({
      where: eq(identities.identifier, identifier),
    });

    if (existing) {
      if (existing.accountId !== accountId) {
        throw new Error('IDENTITY_CONFLICT: This identity is already linked to another account');
      }
      return; // Already linked to this account
    }

    await db.insert(identities).values({
      id: uuidv4(),
      accountId,
      type,
      identifier,
      isPrimary: false,
      linkedAt: new Date().toISOString(),
      verifiedAt: new Date().toISOString(),
    });

    this.logger.log(`✅ Identity linked: ${type}:${identifier} → ${accountId}`);
  }

  /**
   * Resolve identity ke account_id
   */
  async resolveIdentity(type: string, identifier: string): Promise<string | null> {
    const db = getDatabase();

    const identity = await db.query.identities.findFirst({
      where: eq(identities.identifier, identifier),
    });

    return identity?.accountId || null;
  }

  /**
   * Generate recovery codes
   */
  private generateRecoveryCodes(count: number): string[] {
    const codes: string[] = [];
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // No I, O, 1, 0
    
    for (let i = 0; i < count; i++) {
      let code = '';
      for (let j = 0; j < 8; j++) {
        if (j > 0 && j % 4 === 0) code += '-';
        code += chars[Math.floor(Math.random() * chars.length)];
      }
      codes.push(code);
    }
    
    return codes;
  }
}
