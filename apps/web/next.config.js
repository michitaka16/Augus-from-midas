/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  transpilePackages: ["@midas/types", "@midas/tokens"],
};

module.exports = nextConfig;
