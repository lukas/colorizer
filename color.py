from keras.layers import Input, Dense, Flatten, Reshape, Conv2D, UpSampling2D, MaxPooling2D
from keras.models import Model, Sequential
from keras.datasets import mnist
from keras.callbacks import Callback
import random
import glob
import wandb
from wandb.keras import WandbCallback
import subprocess
import os
from PIL import Image
import numpy as np
import cv2
from keras import backend as K
from skimage import io, color

run = wandb.init(project='colorizer-applied-dl')
config = run.config

config.num_epochs = 1
config.batch_size = 4
config.img_dir = "images"
config.height = 256
config.width = 256

val_dir = 'test'
train_dir = 'train'

# automatically get the data if it doesn't exist
if not os.path.exists("train"):
    print("Downloading flower dataset...")
    subprocess.check_output("curl https://storage.googleapis.com/l2kzone/flowers.tar | tar xz", shell=True)

def my_generator(batch_size, img_dir):
    """A generator that returns black and white images and color images"""
    image_filenames = glob.glob(img_dir + "/*")
    counter = 0
    while True:
        bw_images = np.zeros((batch_size, config.width, config.height))
        color_images = np.zeros((batch_size, config.width, config.height, 3))
        random.shuffle(image_filenames) 
        if ((counter+1)*batch_size>=len(image_filenames)):
              counter = 0
        for i in range(batch_size):
              img = Image.open(image_filenames[counter + i]).resize((config.width, config.height))
              color_images[i] = np.array(img)
              bw_images[i] = np.array(img.convert('L'))
        yield (bw_images, color_images)
        counter += batch_size



model = Sequential()
model.add(Reshape((config.height,config.width,1), input_shape=(config.height,config.width)))
model.add(Conv2D(32, (3, 3), activation='relu', padding='same'))
model.add(MaxPooling2D(2,2))
model.add(Conv2D(32, (3, 3), activation='relu', padding='same'))
model.add(UpSampling2D((2, 2)))
model.add(Conv2D(3, (3, 3), activation='relu', padding='same'))

def perceptual_distance(y_true, y_pred):
    rmean = ( y_true[:,:,:,0] + y_pred[:,:,:,0] ) / 2;
    r = y_true[:,:,:,0] - y_pred[:,:,:,0]
    g = y_true[:,:,:,1] - y_pred[:,:,:,1]
    b = y_true[:,:,:,2] - y_pred[:,:,:,2]
    
    return K.mean(K.sqrt((((512+rmean)*r*r)/256) + 4*g*g + (((767-rmean)*b*b)/256)));

model.compile(optimizer='adam', loss='mse', metrics=[perceptual_distance])

(val_bw_images, val_color_images) = next(my_generator(145, val_dir))

model.fit_generator( my_generator(config.batch_size, train_dir),
                     steps_per_epoch=2,
                     epochs=config.num_epochs, callbacks=[WandbCallback(data_type='image', predictions=16)],
                     validation_data=(val_bw_images, val_color_images))


