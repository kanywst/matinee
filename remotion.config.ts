import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
// x264 at CRF 21: visually lossless for terminal content, and small enough
// to attach to a release or drop into a pull request.
Config.setCodec("h264");
Config.setCrf(21);
