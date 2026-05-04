/** @type {import('next').NextConfig} */
const nextConfig = {
	// Set via npm scripts so dev/build outputs never collide.
	distDir: process.env.NEXT_DIST_DIR || ".next",
	images: {
		unoptimized: true,
	},
	webpack: (config, { dev }) => {
		if (dev) {
			// Windows file-system cache corruption has repeatedly caused missing chunks.
			config.cache = false;
		}
		return config;
	},
};

export default nextConfig;
