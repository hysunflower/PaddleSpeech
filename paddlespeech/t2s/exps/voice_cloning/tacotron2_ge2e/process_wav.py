# Copyright (c) 2021 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
from functools import partial
from multiprocessing import Pool
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from praatio import tgio
from tqdm import tqdm


def get_valid_part(fpath):
    f = tgio.openTextgrid(fpath)

    start = 0
    phone_entry_list = f.tierDict['phones'].entryList
    first_entry = phone_entry_list[0]
    if first_entry.label == "sil":
        start = first_entry.end

    last_entry = phone_entry_list[-1]
    if last_entry.label == "sp":
        end = last_entry.start
    else:
        end = last_entry.end
    return start, end


def process_utterance(fpath, source_dir, target_dir, alignment_dir):
    rel_path = fpath.relative_to(source_dir)
    opath = target_dir / rel_path
    apath = (alignment_dir / rel_path).with_suffix(".TextGrid")
    opath.parent.mkdir(parents=True, exist_ok=True)

    start, end = get_valid_part(apath)
    wav, _ = librosa.load(fpath, sr=22050, offset=start, duration=end - start)
    normalized_wav = wav / np.max(wav) * 0.999
    sf.write(opath, normalized_wav, samplerate=22050, subtype='PCM_16')
    # print(f"{fpath} => {opath}")


def preprocess_aishell3(source_dir, target_dir, alignment_dir):
    source_dir = Path(source_dir).expanduser()
    target_dir = Path(target_dir).expanduser()
    alignment_dir = Path(alignment_dir).expanduser()

    wav_paths = list(source_dir.rglob("*.wav"))
    print(f"there are {len(wav_paths)} audio files in total")
    fx = partial(
        process_utterance,
        source_dir=source_dir,
        target_dir=target_dir,
        alignment_dir=alignment_dir)
    with Pool(16) as p:
        list(
            tqdm(p.imap(fx, wav_paths), total=len(wav_paths), unit="utterance"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process audio in AiShell3, trim silence according to the alignment "
        "files generated by MFA, and normalize volume by peak.")
    parser.add_argument(
        "--input",
        type=str,
        default="~/datasets/aishell3/train/wav",
        help="path of the original audio folder in aishell3.")
    parser.add_argument(
        "--output",
        type=str,
        default="~/datasets/aishell3/train/normalized_wav",
        help="path of the folder to save the processed audio files.")
    parser.add_argument(
        "--alignment",
        type=str,
        default="~/datasets/aishell3/train/alignment",
        help="path of the alignment files.")
    args = parser.parse_args()

    preprocess_aishell3(args.input, args.output, args.alignment)
