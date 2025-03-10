import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.pharmapp.app',
  appName: 'PharmApp',
  webDir: 'staticfiles',
  server: {
    url: 'http://localhost:8000',
    cleartext: true
  }
};

export default config;