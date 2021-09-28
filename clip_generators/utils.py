import argparse
import io
import shlex
import time
from pathlib import Path
from typing import Optional, Tuple, List, Union, Any

import requests
from pydantic import BaseModel

from clip_generators.models.taming_transformers.clip_generator.dreamer import network_list


def fetch(url_or_path):
    if str(url_or_path).startswith('http://') or str(url_or_path).startswith('https://'):
        r = requests.get(url_or_path)
        r.raise_for_status()
        fd = io.BytesIO()
        fd.write(r.content)
        fd.seek(0)
        return fd
    return open(url_or_path, 'rb')


networks = network_list()


class GuidedDiffusionGeneratorArgs(BaseModel):
    skips: int = 0
    dddim_respacing: bool = False


class VQGANGenerationArgs(BaseModel):
    network: str = 'imagenet'
    nb_augment: int = 3
    full_image_loss: bool = True
    crazy_mode: bool = False
    learning_rate: float = 0.05
    init_noise_factor: float = 0.0

    @property
    def config(self):
        return Path('..') / networks[self.network]['config']

    @property
    def checkpoint(self):
        return Path('..') / networks[self.network]['checkpoint']


class GenerationArgs(BaseModel):
    prompts: List[Tuple[str, float]] = []
    steps: int = 500
    network_type: str
    refresh_every: int = 100
    seed: int
    resume_from: Optional[str] = None
    cut: int = 64
    model_arguments: Any


def make_arguments_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('--crazy-mode', type=bool, default=False)
    parser.add_argument('--learning-rate', type=float, default=0.05)
    parser.add_argument('--steps', type=int, default=1000)
    parser.add_argument('--refresh-every', type=int, default=10)
    parser.add_argument('--resume-from', type=str, default=None)
    parser.add_argument('--prompt', action='append', required=True)
    parser.add_argument('--cut', type=int, default=64)
    parser.add_argument('--transforms', type=int, default=1)
    parser.add_argument('--full-image-loss', type=bool, default=True)
    parser.add_argument('--network', type=str, default='imagenet')
    parser.add_argument('--network-type', type=str, default='diffusion')
    parser.add_argument('--ddim', dest='ddim_respacing', action='store_true')
    parser.add_argument('--no-ddim', dest='ddim_respacing', action='store_false')
    parser.add_argument('--seed', type=int, default=int(time.time()))
    parser.add_argument('--skip', type=int, default=0)
    parser.add_argument('--init-noise-factor', type=float, default=0.0)

    parser.set_defaults(ddim_respacing=False, add_noise_to_init=False)
    return parser


def make_model_arguments(parsed_args):
    if parsed_args.network_type == 'legacy':
        return VQGANGenerationArgs(network=parsed_args.network,
                            nb_augments=parsed_args.transforms,
                            full_image_loss=parsed_args.full_image_loss,
                            crazy_mode=parsed_args.crazy_mode,
                            learning_rate=parsed_args.learning_rate,
                            init_noise_factor=parsed_args.init_noise_factor)
    else:
        return GuidedDiffusionGeneratorArgs(skips=parsed_args.skip, ddim_respacing=parsed_args.ddim_respacing)

def parse_prompt_args(prompt: str = '') -> GenerationArgs:
    parser = make_arguments_parser()
    try:
        parsed_args = parser.parse_args(shlex.split(prompt))
        print(parsed_args)
        args = GenerationArgs(prompt=parsed_args.prompt,
                              refresh_every=parsed_args.refresh_every,
                              resume_from=parsed_args.resume_from,
                              steps=parsed_args.steps,
                              cut=parsed_args.cut,
                              network_type=parsed_args.network_type,
                              seed=parsed_args.seed,
                              skips=parsed_args.skip,
                              model_arguments=make_model_arguments(parsed_args)
                              )
        args.prompts = []
        for the_prompt in parsed_args.prompt:
            if ';' in the_prompt:
                separator_index = the_prompt.rindex(';')
                args.prompts.append((the_prompt[:separator_index], float(the_prompt[separator_index + 1:])))
            else:
                args.prompts.append((the_prompt, 1.0))
        return args
    except SystemExit:
        raise Exception(parser.usage())
