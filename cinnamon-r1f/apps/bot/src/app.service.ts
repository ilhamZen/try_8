import { Injectable } from '@nestjs/common';

@Injectable()
export class AppService {
  getHello(): string {
    return 'Cinnamon R1F - WhatsApp Bot Ecosystem';
  }
}
