import PIL.Image
import torch
from torch import optim

from models.taming_transformers.clip_generator.discriminator import ClipDiscriminator
from models.taming_transformers.clip_generator.generator import ZSpace, Generator
from torchvision.transforms import functional as TF
from progressbar import progressbar

device = 'cuda:0'

image_size=(512, 512)


class ImageEditor:
    def __init__(self, vqgan, clip, image):
        self.vqgan = vqgan
        self.clip = clip
        self.init_image = image

        self.generator = Generator(vqgan).to(device)
        self.z_space = ZSpace(generator=self.generator,
                             image_size=image_size,
                             device=device,
                             init_image=image, init_noise_factor=0.0)
        self.clip_discriminator = None

    def load_text(self, text):
        self.clip_discriminator = ClipDiscriminator(self.clip, [(text, 1.0)], 64, 1., device,
                                               full_image_loss=True,
                                               nb_augments=1)

    def edit_image(self, point, learning_rate, steps):
        l1_loss = torch.nn.MSELoss()

        # todo: use box here
        optimizer = optim.Adam([self.z_space.z], lr=learning_rate)
        mask = torch.zeros(self.z_space.z.shape).to(device)
        mask[:, :, 0:10, :] = 1
        mask[:, :, 10:20, :] = 0

        for _ in progressbar(range(steps)):
            generated_image = self.generator(self.z_space.z)
            losses = self.clip_discriminator(generated_image)
            losses.append(l1_loss(generated_image, self.z_space.base_image_decoded) * 0.5)
            sum(losses).backward()
            self.z_space.z.grad *= mask
            optimizer.step()


    def get_image(self) -> PIL.Image.Image:
        generated_image = self.generator(self.z_space.z)
        return TF.to_pil_image(generated_image[0].cpu())
