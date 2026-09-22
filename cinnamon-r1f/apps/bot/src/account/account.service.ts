import { Injectable } from '@nestjs/common';
import { v4 as uuidv4 } from 'uuid';
import * as argon2 from 'argon2';
import { db } from '../../../db/connection';
import { accounts, identities, profiles, wallets } from '../../../db/schema';
import { eq } from 'drizzle-orm';

export interface RegisterDto {
  password: string;
  displayName?: string;
}

export interface LoginDto {
  identifier: string; // LID or PN
  password: string;
}

@Injectable()
export class AccountService {
  /**
   * Register a new account with permanent UUID
   */
  async register(dto: RegisterDto, whatsappIdentity: { type: string; identifier: string }) {
    const accountId = uuidv4();
    const now = new Date().toISOString();

    // Hash password with Argon2id
    const passwordHash = await argon2.hash(dto.password, {
      type: argon2.Type.Argon2id,
      memoryCost: 65536,
      timeCost: 3,
      parallelism: 4,
    });

    // Generate recovery codes
    const recoveryCodes = this.generateRecoveryCodes(10);
    const hashedCodes = await Promise.all(
      recoveryCodes.map(code => argon2.hash(code)),
    );

    // Create account in transaction
    try {
      await db.transaction(async (tx) => {
        // Insert account
        await tx.insert(accounts).values({
          id: accountId,
          passwordHash,
          createdAt: now,
          updatedAt: now,
          status: 'active',
        });

        // Insert identity
        await tx.insert(identities).values({
          id: uuidv4(),
          accountId,
          type: whatsappIdentity.type,
          identifier: whatsappIdentity.identifier,
          isPrimary: true,
          linkedAt: now,
          verifiedAt: now,
        });

        // Insert profile
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

        // Insert wallet
        await tx.insert(wallets).values({
          id: uuidv4(),
          accountId,
          balance: 0,
          bankBalance: 0,
          updatedAt: now,
        });

        // Insert recovery codes
        for (let i = 0; i < hashedCodes.length; i++) {
          await tx.insert(tx.schema.recoveryCodes).values({
            id: uuidv4(),
            accountId,
            codeHash: hashedCodes[i],
            used: false,
            createdAt: now,
          });
        }
      });

      return {
        accountId,
        recoveryCodes, // Return plaintext codes only once
      };
    } catch (error) {
      console.error('Registration failed:', error);
      throw new Error('Registration failed');
    }
  }

  /**
   * Login with identity and password
   */
  async login(identifier: string, password: string) {
    // Find identity
    const [identity] = await db.select().from(identities).where(
      eq(identities.identifier, identifier)
    ).limit(1);

    if (!identity) {
      throw new Error('Identity not found');
    }

    // Find account
    const [account] = await db.select().from(accounts).where(
      eq(accounts.id, identity.accountId)
    ).limit(1);

    if (!account) {
      throw new Error('Account not found');
    }

    if (account.status !== 'active') {
      throw new Error('Account is not active');
    }

    // Verify password
    const validPassword = await argon2.verify(account.passwordHash, password);
    if (!validPassword) {
      throw new Error('Invalid password');
    }

    // Update last login
    await db.update(accounts)
      .set({ 
        lastLoginAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      })
      .where(eq(accounts.id, account.id));

    return {
      accountId: account.id,
      rank: 'user', // Will be fetched from profile
    };
  }

  /**
   * Link new identity to existing account (for LID/PN changes)
   */
  async linkIdentity(accountId: string, identityType: string, identifier: string) {
    const now = new Date().toISOString();

    // Check if identity already exists
    const [existing] = await db.select().from(identities).where(
      eq(identities.identifier, identifier)
    ).limit(1);

    if (existing) {
      if (existing.accountId === accountId) {
        return { success: true, message: 'Identity already linked' };
      } else {
        throw new Error('IDENTITY_CONFLICT: This identity belongs to another account');
      }
    }

    // Link new identity
    await db.insert(identities).values({
      id: uuidv4(),
      accountId,
      type: identityType,
      identifier,
      isPrimary: false,
      linkedAt: now,
      verifiedAt: now,
    });

    return { success: true, message: 'Identity linked successfully' };
  }

  /**
   * Recover account using recovery code
   */
  async recoverAccount(accountId: string, recoveryCode: string, newIdentity?: { type: string; identifier: string }) {
    const now = new Date().toISOString();

    // Get all recovery codes for account
    const codes = await db.select().from(db.schema.recoveryCodes).where(
      eq(db.schema.recoveryCodes.accountId, accountId)
    );

    // Find valid code
    let validCodeId: string | null = null;
    for (const code of codes) {
      if (code.used) continue;
      
      const valid = await argon2.verify(code.codeHash, recoveryCode);
      if (valid) {
        validCodeId = code.id;
        break;
      }
    }

    if (!validCodeId) {
      throw new Error('Invalid or expired recovery code');
    }

    // Mark code as used
    await db.update(db.schema.recoveryCodes)
      .set({ 
        used: true,
        usedAt: now,
      })
      .where(eq(db.schema.recoveryCodes.id, validCodeId));

    // Link new identity if provided
    if (newIdentity) {
      await this.linkIdentity(accountId, newIdentity.type, newIdentity.identifier);
      
      // Set as primary
      await db.update(identities)
        .set({ isPrimary: true })
        .where(
          eq(identities.accountId, accountId) &&
          eq(identities.identifier, newIdentity.identifier)
        );
    }

    return { success: true, message: 'Account recovered successfully' };
  }

  /**
   * Get account by identity
   */
  async getAccountByIdentity(identifier: string) {
    const [identity] = await db.select().from(identities).where(
      eq(identities.identifier, identifier)
    ).limit(1);

    if (!identity) {
      return null;
    }

    const [account] = await db.select().from(accounts).where(
      eq(accounts.id, identity.accountId)
    ).limit(1);

    return account;
  }

  /**
   * Generate recovery codes
   */
  private generateRecoveryCodes(count: number): string[] {
    const codes: string[] = [];
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // No I, O, 0, 1
    
    for (let i = 0; i < count; i++) {
      let code = '';
      for (let j = 0; j < 4; j++) {
        if (j > 0) code += '-';
        for (let k = 0; k < 4; k++) {
          code += chars[Math.floor(Math.random() * chars.length)];
        }
      }
      codes.push(code);
    }
    
    return codes;
  }
}
