#### Main file for END to END training

import argparse
import shutil
import numpy as np
import cv2

from ball_3d_coordinates.end_to_end.preprocessing.data_preprocessing import ConvPreprocessor
from ball_3d_coordinates.end_to_end.preprocessing.data_loader import Loader
from ball_3d_coordinates.end_to_end.model.conv_net import ConvNet
from ball_3d_coordinates.end_to_end.model.conv_lstm_net import ConvLSTMNet

parser = argparse.ArgumentParser()

""" General Parameters """
parser.add_argument('--debug', type=bool, default=False, 
    help='if True debug the model.')
parser.add_argument('--restore', type=bool, default=True, 
    help='if True restore the model from --model_path.')
parser.add_argument('--test', type=bool, default=False, 
    help='if True test the model.')
parser.add_argument('--train', type=bool, default=True, 
    help='if True train the model.')
parser.add_argument('--tune', type=bool, default=False, 
    help='if True tune the model.')
parser.add_argument('--create_df', type=bool, default=False, 
    help='if True creates a dataframe with the prediction of the model.')

""" Model Parametes """
parser.add_argument('--log_dir', type=str, default='./tensorbaord', 
    help='directory where to store tensorbaord values.')
parser.add_argument('--model_path', type=str, 
    default='./ball_3d_coordinates/end_to_end/weights/img_net', 
    help='model checkpoints directory.')
parser.add_argument('--epochs', type=int, default=500, 
    help='number of batch iterations.')
parser.add_argument('--batch_size', type=int, default=1, 
    help='number of samples in the training batch.')
parser.add_argument('--input_trace', type=int, default=15, 
    help='length of the sequence.')
parser.add_argument('--number_of_samples', type=int, default=200, 
    help='how many frames you want to load for the prediction using the convnet.')

args = parser.parse_args()

def main():

    # Remove Tensorboard Folder
    try:
        shutil.rmtree('./tensorbaord')
    except FileNotFoundError:
        pass
    
    # Fix the seed
    np.random.seed(0)

    # Load the data
    loader = Loader(number_of_samples=args.number_of_samples)
    X, y = loader.load_data()
    print("Loaded the data...")

    # Saving Maximum values for later debugging
    MAX_X = y["x"].max()
    MAX_Y = y["y"].max()
    MAX_Z = y["z"].max()

    # Visulize the Labels DF
    print(y.describe())

    # Preprocess the data
    preprocessor = ConvPreprocessor(MAX_X, MAX_Y, MAX_Z, args.input_trace)
    X_train, y_train, X_test, y_test, X_val, y_val = preprocessor.fit_transform(X, y)

    print(X_train.shape)
    # Define the Model
    model = ConvLSTMNet(
        batch_size=args.batch_size,
        input_trace=args.input_trace,
        epochs=args.epochs,
        log_dir=args.log_dir,
        model_path=args.model_path
        )

    # Get Validation data
    X_val = loader.get_image_features(X_val)
    X_val = preprocessor.preprocess_images(X_val)

    batch_memory_dimension = 50
    for i in range(0, len(X_train)-batch_memory_dimension, batch_memory_dimension):
        
        # Get data
        X = loader.get_image_features(X_train[i:i+batch_memory_dimension])
        y = y_train[i:i+batch_memory_dimension,:]

        # Preprocess Images
        X = preprocessor.preprocess_images(X)

        # Restore the model
        if args.restore == True:
            model.restore()

        # Train the model
        if args.train == True:
            history = model.fit(X, y, X_val, y_val)

    # Tune the model
    if args.tune == True:
        model.tune(X_train, y_train)

    # Test the model
    if args.test == True:
        model.evaluate(X_test, y_test)

    # Debug the model
    if args.debug == True:
        model.debug(X_test, y_test)

    # Create the DF for the next model
    if args.create_df == True:
        model.create_df(X)
    
    return

main()
