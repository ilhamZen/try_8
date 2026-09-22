import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { DbModule } from './db/db.module';
import { AccountModule } from './account/account.module';
import { PermissionModule } from './permission/permission.module';
import { ProfileModule } from './profile/profile.module';
import { EconomyModule } from './economy/economy.module';

@Module({
  imports: [
    DbModule,
    AccountModule,
    PermissionModule,
    ProfileModule,
    EconomyModule,
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
