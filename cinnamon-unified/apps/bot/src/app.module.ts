import { Module } from '@nestjs/common';
import { AppService } from './app.service';

// Core Modules
import { AccountModule } from './account/account.module';
import { IdentityModule } from './identity/identity.module';
import { PermissionModule } from './permission/permission.module';
import { ProfileModule } from './profile/profile.module';

// Economy & Inventory
import { EconomyModule } from './economy/economy.module';
import { InventoryModule } from './inventory/inventory.module';

// Progression
import { ProgressionModule } from './progression/progression.module';
import { ReputationModule } from './reputation/reputation.module';

// Games & RPG
import { RpgModule } from './rpg/rpg.module';
import { GameModule } from './game/game.module';
import { FishingModule } from './fishing/fishing.module';
import { MiningModule } from './mining/mining.module';

// Group & Social
import { GroupModule } from './group/group.module';
import { MoModule } from './mo/mo.module';
import { OwnerModule } from './owner/owner.module';

// Media & Utility
import { MediaModule } from './media/media.module';
import { DownloaderModule } from './downloader/downloader.module';
import { UtilityModule } from './utility/utility.module';

// Infrastructure
import { CommandsModule } from './commands/commands.module';
import { WhatsappModule } from './whatsapp/whatsapp.module';
import { EventsModule } from './events/events.module';
import { UiModule } from './ui/ui.module';

@Module({
  imports: [
    // Infrastructure
    WhatsappModule,
    CommandsModule,
    EventsModule,
    UiModule,
    
    // Core
    AccountModule,
    IdentityModule,
    PermissionModule,
    ProfileModule,
    
    // Economy & Inventory
    EconomyModule,
    InventoryModule,
    
    // Progression
    ProgressionModule,
    ReputationModule,
    
    // Games & RPG
    RpgModule,
    GameModule,
    FishingModule,
    MiningModule,
    
    // Group & Social
    GroupModule,
    MoModule,
    OwnerModule,
    
    // Media & Utility
    MediaModule,
    DownloaderModule,
    UtilityModule,
  ],
  providers: [AppService],
})
export class AppModule {}
