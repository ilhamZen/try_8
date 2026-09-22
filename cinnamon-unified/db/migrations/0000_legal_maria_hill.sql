CREATE TABLE `account_achievements` (
	`id` text PRIMARY KEY NOT NULL,
	`account_id` text NOT NULL,
	`achievement_id` text NOT NULL,
	`completed_at` text NOT NULL,
	`claimed_at` text,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`achievement_id`) REFERENCES `achievements`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `account_quests` (
	`id` text PRIMARY KEY NOT NULL,
	`account_id` text NOT NULL,
	`quest_id` text NOT NULL,
	`progress` integer DEFAULT 0 NOT NULL,
	`completed` integer DEFAULT false NOT NULL,
	`claimed_at` text,
	`expires_at` text,
	`started_at` text NOT NULL,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`quest_id`) REFERENCES `quests`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `account_skills` (
	`id` text PRIMARY KEY NOT NULL,
	`account_id` text NOT NULL,
	`skill_id` text NOT NULL,
	`level` integer DEFAULT 1 NOT NULL,
	`unlocked_at` text NOT NULL,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`skill_id`) REFERENCES `skills`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `account_titles` (
	`id` text PRIMARY KEY NOT NULL,
	`account_id` text NOT NULL,
	`title_id` text NOT NULL,
	`unlocked_at` text NOT NULL,
	`is_equipped` integer DEFAULT false NOT NULL,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`title_id`) REFERENCES `titles`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `accounts` (
	`id` text PRIMARY KEY NOT NULL,
	`password_hash` text NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	`last_login_at` text,
	`status` text DEFAULT 'active' NOT NULL
);
--> statement-breakpoint
CREATE TABLE `achievements` (
	`id` text PRIMARY KEY NOT NULL,
	`namespace` text NOT NULL,
	`name` text NOT NULL,
	`description` text,
	`requirement` text NOT NULL,
	`reward_xp` integer DEFAULT 0 NOT NULL,
	`reward_cash` integer DEFAULT 0 NOT NULL,
	`reward_title_id` text
);
--> statement-breakpoint
CREATE TABLE `event_log` (
	`id` text PRIMARY KEY NOT NULL,
	`account_id` text NOT NULL,
	`event_type` text NOT NULL,
	`event_data` text,
	`processed_at` text NOT NULL,
	`created_at` text NOT NULL,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `game_results` (
	`id` text PRIMARY KEY NOT NULL,
	`session_id` text NOT NULL,
	`account_id` text NOT NULL,
	`result` text NOT NULL,
	`reward` integer DEFAULT 0 NOT NULL,
	`created_at` text NOT NULL,
	FOREIGN KEY (`session_id`) REFERENCES `game_sessions`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `game_sessions` (
	`id` text PRIMARY KEY NOT NULL,
	`account_id` text NOT NULL,
	`game_id` text NOT NULL,
	`group_id` text,
	`state` text DEFAULT 'idle' NOT NULL,
	`bet_amount` integer DEFAULT 0 NOT NULL,
	`game_state` text,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	`completed_at` text,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`game_id`) REFERENCES `games`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `games` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`type` text NOT NULL,
	`min_bet` integer DEFAULT 0 NOT NULL,
	`max_bet` integer DEFAULT 10000 NOT NULL,
	`enabled` integer DEFAULT true NOT NULL
);
--> statement-breakpoint
CREATE TABLE `group_permissions` (
	`id` text PRIMARY KEY NOT NULL,
	`account_id` text NOT NULL,
	`group_id` text NOT NULL,
	`permission` text NOT NULL,
	`granted_by` text NOT NULL,
	`granted_at` text NOT NULL,
	`expires_at` text,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`group_id`) REFERENCES `groups`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `groups` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text,
	`settings` text,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `idempotency_keys` (
	`id` text PRIMARY KEY NOT NULL,
	`key` text NOT NULL,
	`account_id` text NOT NULL,
	`operation` text NOT NULL,
	`result` text,
	`created_at` text NOT NULL,
	`expires_at` text NOT NULL,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `idempotency_keys_key_unique` ON `idempotency_keys` (`key`);--> statement-breakpoint
CREATE TABLE `identities` (
	`id` text PRIMARY KEY NOT NULL,
	`account_id` text NOT NULL,
	`type` text NOT NULL,
	`identifier` text NOT NULL,
	`is_primary` integer DEFAULT false NOT NULL,
	`linked_at` text NOT NULL,
	`verified_at` text,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `inventory` (
	`id` text PRIMARY KEY NOT NULL,
	`account_id` text NOT NULL,
	`item_id` text NOT NULL,
	`quantity` integer DEFAULT 1 NOT NULL,
	`acquired_at` text NOT NULL,
	`metadata` text,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`item_id`) REFERENCES `items`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `items` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`type` text NOT NULL,
	`rarity` text DEFAULT 'common' NOT NULL,
	`stack_limit` integer DEFAULT 1 NOT NULL,
	`sell_price` integer DEFAULT 0 NOT NULL,
	`effects` text,
	`metadata` text
);
--> statement-breakpoint
CREATE TABLE `mini_owners` (
	`id` text PRIMARY KEY NOT NULL,
	`account_id` text NOT NULL,
	`group_id` text NOT NULL,
	`plan` text NOT NULL,
	`started_at` text NOT NULL,
	`expires_at` text,
	`permissions` text,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`group_id`) REFERENCES `groups`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `profiles` (
	`id` text PRIMARY KEY NOT NULL,
	`account_id` text NOT NULL,
	`display_name` text,
	`rank` text DEFAULT 'user' NOT NULL,
	`title_id` text,
	`level` integer DEFAULT 1 NOT NULL,
	`xp` integer DEFAULT 0 NOT NULL,
	`reputation` integer DEFAULT 0 NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `quests` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`description` text,
	`type` text NOT NULL,
	`objective` text NOT NULL,
	`reward_xp` integer DEFAULT 0 NOT NULL,
	`reward_cash` integer DEFAULT 0 NOT NULL,
	`reward_item_id` text,
	`reward_item_quantity` integer DEFAULT 1
);
--> statement-breakpoint
CREATE TABLE `recovery_codes` (
	`id` text PRIMARY KEY NOT NULL,
	`account_id` text NOT NULL,
	`code_hash` text NOT NULL,
	`used` integer DEFAULT false NOT NULL,
	`used_at` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `rpg_profiles` (
	`id` text PRIMARY KEY NOT NULL,
	`account_id` text NOT NULL,
	`class` text DEFAULT 'warrior' NOT NULL,
	`hp` integer DEFAULT 100 NOT NULL,
	`max_hp` integer DEFAULT 100 NOT NULL,
	`atk` integer DEFAULT 10 NOT NULL,
	`def` integer DEFAULT 5 NOT NULL,
	`crit` integer DEFAULT 5 NOT NULL,
	`luck` integer DEFAULT 5 NOT NULL,
	`weapon_id` text,
	`armor_id` text,
	`accessory_id` text,
	`updated_at` text NOT NULL,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `season_progress` (
	`id` text PRIMARY KEY NOT NULL,
	`account_id` text NOT NULL,
	`season_id` text NOT NULL,
	`tier` integer DEFAULT 1 NOT NULL,
	`progress` integer DEFAULT 0 NOT NULL,
	`max_progress` integer NOT NULL,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`season_id`) REFERENCES `seasons`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `seasons` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`start_date` text NOT NULL,
	`end_date` text NOT NULL,
	`is_active` integer DEFAULT false NOT NULL
);
--> statement-breakpoint
CREATE TABLE `skills` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`category` text NOT NULL,
	`tier` text DEFAULT 'I' NOT NULL,
	`prerequisite_skill_id` text,
	`cost` integer NOT NULL,
	`effect` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `titles` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`description` text,
	`rarity` text DEFAULT 'common' NOT NULL,
	`unlock_requirement` text
);
--> statement-breakpoint
CREATE TABLE `transactions` (
	`id` text PRIMARY KEY NOT NULL,
	`account_id` text NOT NULL,
	`type` text NOT NULL,
	`amount` integer NOT NULL,
	`balance_before` integer NOT NULL,
	`balance_after` integer NOT NULL,
	`source` text NOT NULL,
	`reference` text,
	`created_at` text NOT NULL,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `wallets` (
	`id` text PRIMARY KEY NOT NULL,
	`account_id` text NOT NULL,
	`balance` integer DEFAULT 0 NOT NULL,
	`bank_balance` integer DEFAULT 0 NOT NULL,
	`updated_at` text NOT NULL,
	FOREIGN KEY (`account_id`) REFERENCES `accounts`(`id`) ON UPDATE no action ON DELETE no action
);
