import fs from 'node:fs';
import { pipeline, env } from '@huggingface/transformers';
import wav from 'wav-decoder';

env.allowLocalModels = false;
env.remoteHost = process.env.HF_ENDPOINT || 'https://hf-mirror.com/';
env.backends.onnx.wasm.numThreads = Math.max(1, Number(process.env.WHISPER_THREADS || '4'));

const input = process.argv[2];
const modelName = process.argv[3] || 'onnx-community/whisper-base';
if (!input) {
  throw new Error('Usage: node transformers_whisper_asr.mjs audio.wav [model]');
}

const buffer = fs.readFileSync(input);
const decoded = await wav.decode(buffer);
const channel = decoded.channelData.length === 1
  ? decoded.channelData[0]
  : decoded.channelData[0].map((value, index) => {
      const right = decoded.channelData[1][index] ?? value;
      return (value + right) / 2;
    });

const transcriber = await pipeline('automatic-speech-recognition', modelName, {
  dtype: 'q8',
});

const result = await transcriber(channel, {
  sampling_rate: decoded.sampleRate,
  language: 'zh',
  task: 'transcribe',
  return_timestamps: true,
  chunk_length_s: 30,
  stride_length_s: 5,
});

const chunks = Array.isArray(result.chunks) ? result.chunks : [];
const payload = chunks
  .map((chunk) => {
    const timestamp = Array.isArray(chunk.timestamp) ? chunk.timestamp : [0, 0];
    return {
      text: String(chunk.text || '').trim(),
      start: Number(timestamp[0] || 0),
      end: Number(timestamp[1] || timestamp[0] || 0),
      confidence: 0.0,
    };
  })
  .filter((chunk) => chunk.text.length > 0 && chunk.end >= chunk.start);

process.stdout.write(JSON.stringify(payload));
