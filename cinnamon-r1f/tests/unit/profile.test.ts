import { describe, it, expect } from 'vitest';
import { ProfileService } from '../apps/bot/src/profile/profile.service';

describe('Profile Service', () => {
  let profileService: ProfileService;

  beforeEach(() => {
    profileService = new ProfileService();
  });

  describe('getReputationTier', () => {
    it('should return Unknown for reputation 0-199', () => {
      expect(profileService.getReputationTier(0)).toBe('Unknown');
      expect(profileService.getReputationTier(100)).toBe('Unknown');
      expect(profileService.getReputationTier(199)).toBe('Unknown');
    });

    it('should return Friendly for reputation 200-399', () => {
      expect(profileService.getReputationTier(200)).toBe('Friendly');
      expect(profileService.getReputationTier(300)).toBe('Friendly');
      expect(profileService.getReputationTier(399)).toBe('Friendly');
    });

    it('should return Trusted for reputation 400-599', () => {
      expect(profileService.getReputationTier(400)).toBe('Trusted');
      expect(profileService.getReputationTier(500)).toBe('Trusted');
      expect(profileService.getReputationTier(599)).toBe('Trusted');
    });

    it('should return Honored for reputation 600-749', () => {
      expect(profileService.getReputationTier(600)).toBe('Honored');
      expect(profileService.getReputationTier(700)).toBe('Honored');
      expect(profileService.getReputationTier(749)).toBe('Honored');
    });

    it('should return Respected for reputation 750-899', () => {
      expect(profileService.getReputationTier(750)).toBe('Respected');
      expect(profileService.getReputationTier(800)).toBe('Respected');
      expect(profileService.getReputationTier(899)).toBe('Respected');
    });

    it('should return Legendary for reputation 900-1000', () => {
      expect(profileService.getReputationTier(900)).toBe('Legendary');
      expect(profileService.getReputationTier(950)).toBe('Legendary');
      expect(profileService.getReputationTier(1000)).toBe('Legendary');
    });

    it('should cap reputation at boundaries', () => {
      expect(profileService.getReputationTier(-100)).toBe('Unknown');
      expect(profileService.getReputationTier(1500)).toBe('Legendary');
    });
  });
});
