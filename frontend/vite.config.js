import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

// https://vite.dev/config/
export default defineConfig({
	plugins: [
		react(),
		VitePWA({
			injectRegister: null,
			registerType: "autoUpdate",
			workbox: {
				skipWaiting: true,
				clientsClaim: true,
				cleanupOutdatedCaches: true,
				globPatterns: ["**/*.{js,css,html,ico,png,svg}"],
				runtimeCaching: [
					{
						urlPattern: ({ request }) =>
							request.destination === "document" ||
							request.destination === "script" ||
							request.destination === "style" ||
							request.destination === "image" ||
							request.destination === "font",
						handler: "StaleWhileRevalidate",
						options: {
							cacheName: "app-shell",
						},
					},
					{
						urlPattern: /\/api\//,
						handler: "NetworkFirst",
						options: {
							cacheName: "api-cache",
							networkTimeoutSeconds: 3,
							cacheableResponse: { statuses: [0, 200] },
						},
					},
				],
			},
			manifest: {
				name: "HackathonHero",
				short_name: "HackHero",
				description: "Local & offline hackathon agent",
				theme_color: "#0f172a",
				background_color: "#ffffff",
				display: "standalone",
				start_url: "/",
				scope: "/",
				icons: [
					// Using SVG here as placeholder; you can replace with PNG icons in /public
					{
						src: "/vite.svg",
						sizes: "192x192",
						type: "image/svg+xml",
						purpose: "any",
					},
					{
						src: "/vite.svg",
						sizes: "512x512",
						type: "image/svg+xml",
						purpose: "any",
					},
				],
			},
		}),
	],
	server: {
		proxy: {
			"/api": {
				target: "http://127.0.0.1:8000",
				changeOrigin: true,
				rewrite: (path) => path,
			},
		},
	},
});
