import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		proxy: {
			'/api': {
				target: process.env.API_BASE_URL || 'http://localhost:8000',
				changeOrigin: true
			}
		}
	}
});
