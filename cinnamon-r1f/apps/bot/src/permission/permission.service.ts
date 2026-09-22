import { Injectable } from '@nestjs/common';
import { db } from '../../../db/connection';
import { groupPermissions, miniOwners } from '../../../db/schema';
import { eq, and } from 'drizzle-orm';

export interface PermissionContext {
  groupId?: string;
  [key: string]: any;
}

@Injectable()
export class PermissionService {
  /**
   * Check if account has permission in given context
   */
  async can(accountId: string, permission: string, context?: PermissionContext): Promise<boolean> {
    // Owner has all permissions (check from profiles table)
    const profile = await this.getAccountProfile(accountId);
    
    if (profile?.rank === 'owner') {
      return true;
    }

    // Check mini-owner permissions for group context
    if (context?.groupId) {
      // Check if user is mini-owner for this group
      const mo = await this.getMiniOwner(accountId, context.groupId);
      
      if (mo) {
        // Check if MO hasn't expired
        if (mo.expiresAt && new Date(mo.expiresAt) < new Date()) {
          // MO expired, revoke permissions
          await this.revokeMiniOwner(mo.id);
          return false;
        }

        // Check if permission is in MO permissions
        const permissions = JSON.parse(mo.permissions || '[]');
        if (permissions.includes(permission)) {
          return true;
        }
      }

      // Check explicit group permissions
      const groupPerm = await this.getGroupPermission(accountId, context.groupId, permission);
      if (groupPerm) {
        // Check if permission hasn't expired
        if (groupPerm.expiresAt && new Date(groupPerm.expiresAt) < new Date()) {
          return false;
        }
        return true;
      }
    }

    // Default deny
    return false;
  }

  /**
   * Grant permission to account in context
   */
  async grantPermission(
    accountId: string, 
    permission: string, 
    grantedBy: string, 
    context?: PermissionContext,
    expiresAt?: string
  ) {
    const now = new Date().toISOString();

    if (context?.groupId) {
      await db.insert(groupPermissions).values({
        id: crypto.randomUUID(),
        accountId,
        groupId: context.groupId,
        permission,
        grantedBy,
        grantedAt: now,
        expiresAt: expiresAt || null,
      });
    }
  }

  /**
   * Revoke permission from account
   */
  async revokePermission(accountId: string, permission: string, context?: PermissionContext) {
    if (context?.groupId) {
      await db.delete(groupPermissions).where(
        and(
          eq(groupPermissions.accountId, accountId),
          eq(groupPermissions.groupId, context.groupId),
          eq(groupPermissions.permission, permission)
        )
      );
    }
  }

  /**
   * Set mini-owner for group
   */
  async setMiniOwner(
    accountId: string,
    groupId: string,
    plan: string,
    permissions: string[],
    expiresAt?: string
  ) {
    const now = new Date().toISOString();

    await db.insert(miniOwners).values({
      id: crypto.randomUUID(),
      accountId,
      groupId,
      plan,
      startedAt: now,
      expiresAt: expiresAt || null,
      permissions: JSON.stringify(permissions),
    });
  }

  /**
   * Get account profile
   */
  private async getAccountProfile(accountId: string) {
    const profiles = await db.select().from(db.schema.profiles).where(
      eq(db.schema.profiles.accountId, accountId)
    ).limit(1);

    return profiles[0] || null;
  }

  /**
   * Get mini-owner record
   */
  private async getMiniOwner(accountId: string, groupId: string) {
    const mos = await db.select().from(miniOwners).where(
      and(
        eq(miniOwners.accountId, accountId),
        eq(miniOwners.groupId, groupId)
      )
    ).limit(1);

    return mos[0] || null;
  }

  /**
   * Revoke mini-owner
   */
  private async revokeMiniOwner(moId: string) {
    await db.delete(miniOwners).where(
      eq(miniOwners.id, moId)
    );
  }

  /**
   * Get group permission
   */
  private async getGroupPermission(accountId: string, groupId: string, permission: string) {
    const perms = await db.select().from(groupPermissions).where(
      and(
        eq(groupPermissions.accountId, accountId),
        eq(groupPermissions.groupId, groupId),
        eq(groupPermissions.permission, permission)
      )
    ).limit(1);

    return perms[0] || null;
  }
}
