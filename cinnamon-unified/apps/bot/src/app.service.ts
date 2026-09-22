import { Injectable, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import { Logger } from 'pino';

@Injectable()
export class AppService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger({ 
    level: process.env.LOG_LEVEL || 'info',
    name: 'AppService',
  });

  async onModuleInit() {
    this.logger.info('🍂 Cinnamon R1F initialized');
  }

  async onModuleDestroy() {
    this.logger.warn('🍂 Cinnamon R1F shutting down');
  }

  getHealthStatus(): { status: string; uptime: number } {
    return {
      status: 'healthy',
      uptime: process.uptime(),
    };
  }
}
