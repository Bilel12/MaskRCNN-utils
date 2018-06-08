
# ### See https://github.com/aleju/imgaug and http://imgaug.readthedocs.io/en/latest/index.html
import imgaug
from imgaug import augmenters as iaa
import numpy as np
import glob
import imageio
import os
import argparse
import shutil

IMAGE_EDGE_LENGTH = 1300
NUMBER_OF_IMAGE_CHANNELS = 3
NUMBER_OF_MASK_CHANNELS = 1

parser = argparse.ArgumentParser(description='Create an augmented data set.')
parser.add_argument('-id','--input_directory', type=str, help='Base directory of the images to be augmented.', required=True)
parser.add_argument('-od','--output_directory', type=str, help='Base directory of the output.', required=True)
parser.add_argument('-na','--number_of_augmented_images_per_original', type=int, default=1, help='Number of augmented image/mask pairs to produce for each input image/mask pair.', required=False)
args = parser.parse_args()

image_file_list = glob.glob("{}/images/*.png".format(args.input_directory))
mask_file_list = glob.glob("{}/masks/*.png".format(args.input_directory))

# remove all previous augmentations in this base directory
if os.path.exists(args.output_directory):
    shutil.rmtree(args.output_directory)

# create a new directory structure
augmented_images_directory = "{}/images".format(args.output_directory)
augmented_masks_directory = "{}/masks".format(args.output_directory)
os.makedirs(augmented_images_directory)
os.makedirs(augmented_masks_directory)        

# create the augmentation sequences
affine_seq = iaa.Sequential([
    iaa.Fliplr(0.5), # horizontally flip 50% of the images
    iaa.Flipud(0.5),
    iaa.Affine(rotate=(-120, 120)) # rotate images between -120 and +120 degrees
], random_order=True)

colour_seq = iaa.Sequential([
    iaa.ContrastNormalization((0.5, 1.5), per_channel=0.5), # normalize contrast by a factor of 0.5 to 1.5, sampled randomly per image and for 50% of all images also independently per channel
    iaa.Multiply((0.5, 1.5), per_channel=0.5), # multiply 50% of all images with a random value between 0.5 and 1.5 and multiply the remaining 50% channel-wise, i.e. sample one multiplier independently per channel
    iaa.Add((-40, 40), per_channel=0.5) # add random values between -40 and 40 to images. In 50% of all images the values differ per channel (3 sampled value). In the other 50% of all images the value is the same for all channels
], random_order=True)

# go through all the images and create a set of augmented images and masks for each
for idx in range(len(image_file_list)):
    augmented_images = []
    augmented_masks = []

    base_name = os.path.basename(image_file_list[idx])
    print("processing {} ({} of {})".format(base_name, idx, len(image_file_list)))

    base_image = imageio.imread(image_file_list[idx])
    base_mask = imageio.imread(mask_file_list[idx])

    # make sure all the images and masks are the same shape
    if base_image.shape[1] != IMAGE_EDGE_LENGTH:
        new_base_image = np.zeros((IMAGE_EDGE_LENGTH, IMAGE_EDGE_LENGTH, NUMBER_OF_IMAGE_CHANNELS), dtype=np.uint8)
        new_base_image[:base_image.shape[0],:base_image.shape[1],:base_image.shape[2]] = base_image
        base_image = new_base_image

        # from the imgaug doco: "grayscale images must have shape (height, width, 1) each."
        new_base_mask = np.zeros((IMAGE_EDGE_LENGTH, IMAGE_EDGE_LENGTH, NUMBER_OF_MASK_CHANNELS), dtype=np.uint8)
        new_base_mask[:base_mask.shape[0],:base_mask.shape[1],0] = base_mask
        base_mask = new_base_mask
    else:
        base_mask.shape = (IMAGE_EDGE_LENGTH, IMAGE_EDGE_LENGTH, 1)
    
    images_list = []
    masks_list = []
    for i in range(args.number_of_augmented_images_per_original):
        images_list.append(base_image)
        masks_list.append(base_mask)
        
    # convert the image lists to an array of images as expected by imgaug
    images = np.stack(images_list, axis=0)
    masks = np.stack(masks_list, axis=0)

    # Convert the stochastic sequence of augmenters to a deterministic one.
    # The deterministic sequence will always apply the exactly same effects to the images.
    affine_det = affine_seq.to_deterministic() # call this for each batch again, NOT only once at the start

    images_aug = affine_det.augment_images(images)
    masks_aug = affine_det.augment_images(masks)
    
    # apply the colour augmentations to the images but not the masks
    images_aug = colour_seq.augment_images(images_aug)
    
    # write out the un-augmented image/mask pair
    print("writing out the un-augmented image/mask pair")
    output_base_name = "{}_orig{}".format(os.path.splitext(base_name)[0], os.path.splitext(base_name)[1])
    imageio.imwrite("{}/{}".format(augmented_images_directory,output_base_name), base_image)
    imageio.imwrite("{}/{}".format(augmented_masks_directory,output_base_name), base_mask)
    
    # now write out the augmented image/mask pairs
    print("writing out the augmented image/mask pairs")
    for i in range(args.number_of_augmented_images_per_original):
        output_base_name = "{}_augm_{}{}".format(os.path.splitext(base_name)[0], i, os.path.splitext(base_name)[1])
        imageio.imwrite("{}/{}".format(augmented_images_directory,output_base_name), images_aug[i])
        imageio.imwrite("{}/{}".format(augmented_masks_directory,output_base_name), masks_aug[i])
