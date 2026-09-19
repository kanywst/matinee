import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
// x264 at CRF 21 matches the encode preset documented in docs/04-dev-stack.md.
Config.setCodec("h264");
Config.setCrf(21);
