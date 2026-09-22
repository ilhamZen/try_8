import { Injectable } from '@nestjs/common';
import { db } from '../../../db/connection';
import { profiles, titles, accountTitles } from '../../../db/schema';
import { eq } from 'drizzle-orm';

export interface ProfileData {
  accountId: string;
  displayName: string | null;
  rank: string;
  titleId: string | null;
  titleName: string | null;
  level: number;
  xp: number;
  reputation: number;
}

@Injectable()
export class ProfileService {
  /**
   * Get full profile for account
   */
  async getProfile(accountId: string): Promise<ProfileData | null> {
    const [profile] = await db.select().from(profiles).where(
      eq(profiles.accountId, accountId)
    ).limit(1);

    if (!profile) {
      return null;
    }

    // Get equipped title name if exists
    let titleName: string | null = null;
    if (profile.titleId) {
      const [title] = await db.select().from(titles).where(
        eq(titles.id, profile.titleId)
      ).limit(1);
      
      if (title) {
        titleName = title.name;
      }
    }

    return {
      accountId: profile.accountId,
      displayName: profile.displayName,
      rank: profile.rank,
      titleId: profile.titleId,
      titleName,
      level: profile.level,
      xp: profile.xp,
      reputation: profile.reputation,
    };
  }

  /**
   * Update display name
   */
  async updateDisplayName(accountId: string, displayName: string) {
    await db.update(profiles)
      .set({ 
        displayName,
        updatedAt: new Date().toISOString(),
      })
      .where(eq(profiles.accountId, accountId));
  }

  /**
   * Equip title
   */
  async equipTitle(accountId: string, titleId: string) {
    // Check if user owns this title
    const [owned] = await db.select().from(accountTitles).where(
      eq(accountTitles.accountId, accountId) &&
      eq(accountTitles.titleId, titleId)
    ).limit(1);

    if (!owned) {
      throw new Error('Title not owned');
    }

    // Unequip all other titles
    await db.update(accountTitles)
      .set({ isEquipped: false })
      .where(eq(accountTitles.accountId, accountId));

    // Equip selected title
    await db.update(accountTitles)
      .set({ isEquipped: true })
      .where(
        eq(accountTitles.accountId, accountId) &&
        eq(accountTitles.titleId, titleId)
      );

    // Update profile
    await db.update(profiles)
      .set({ 
        titleId,
        updatedAt: new Date().toISOString(),
      })
      .where(eq(profiles.accountId, accountId));
  }

  /**
   * Add XP to profile
   */
  async addXp(accountId: string, amount: number) {
    const [profile] = await db.select().from(profiles).where(
      eq(profiles.accountId, accountId)
    ).limit(1);

    if (!profile) {
      throw new Error('Profile not found');
    }

    const newXp = profile.xp + amount;
    const xpForNextLevel = profile.level * 100;
    
    let newLevel = profile.level;
    let remainingXp = newXp;

    // Level up logic
    while (remainingXp >= xpForNextLevel) {
      remainingXp -= xpForNextLevel;
      newLevel++;
    }

    await db.update(profiles)
      .set({
        level: newLevel,
        xp: remainingXp,
        updatedAt: new Date().toISOString(),
      })
      .where(eq(profiles.accountId, accountId));

    return {
      oldLevel: profile.level,
      newLevel,
      newXp: remainingXp,
    };
  }

  /**
   * Add reputation
   */
  async addReputation(accountId: string, amount: number) {
    const [profile] = await db.select().from(profiles).where(
      eq(profiles.accountId, accountId)
    ).limit(1);

    if (!profile) {
      throw new Error('Profile not found');
    }

    const newRep = Math.max(0, Math.min(1000, profile.reputation + amount));

    await db.update(profiles)
      .set({
        reputation: newRep,
        updatedAt: new Date().toISOString(),
      })
      .where(eq(profiles.accountId, accountId));

    return newRep;
  }

  /**
   * Get reputation tier
   */
  getReputationTier(reputation: number): string {
    if (reputation >= 900) return 'Legendary';
    if (reputation >= 750) return 'Respected';
    if (reputation >= 600) return 'Honored';
    if (reputation >= 400) return 'Trusted';
    if (reputation >= 200) return 'Friendly';
    return 'Unknown';
  }
}
