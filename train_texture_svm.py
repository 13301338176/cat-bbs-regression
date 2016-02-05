"""
Script to train an SVM classifier to locate cat faces in images.
The classifiers training data consists of HOGs of crops of images (windows).
It has to predict 1 (contains cat) whenever the fraction of pixels that
show a cat (in a window) is above a threshold (20 percent by default).
Usage:
    python train_hog_svm.py --dataset="/path/to/images-directory"
"""
from __future__ import absolute_import, division, print_function
from dataset import Dataset
import numpy as np
import argparse
import random
import os
from skimage.feature import greycomatrix, greycoprops
from sklearn.svm import SVC
from train_hog_svm import get_crops_with_labels

np.random.seed(42)
random.seed(42)

MODEL_IMAGE_HEIGHT = 512
MODEL_IMAGE_WIDTH = 512
CROP_HEIGHT = 32
CROP_WIDTH = 32
NB_CROPS = 7500
NB_VALIDATION = 512
NB_AUGMENTATIONS = 0
CAT_FRACTION_THRESHOLD = 0.5

def main():
    """Load images, train classifier, score classifier."""
    parser = argparse.ArgumentParser(description="Train an SVM model to locate cat faces in images based on texture characteristics.")
    parser.add_argument("--dataset", required=True, help="Path to your 10k cats dataset directory")
    args = parser.parse_args()

    # initialize dataset
    subdir_names = ["CAT_00", "CAT_01", "CAT_02", "CAT_03", "CAT_04", "CAT_05", "CAT_06"]
    subdirs = [os.path.join(args.dataset, subdir) for subdir in subdir_names]
    dataset = Dataset(subdirs)

    # load images and labels
    print("Loading images...")
    X, y = load_xy(dataset, NB_CROPS, NB_AUGMENTATIONS)
    assert X.dtype == np.float32
    print("X min:", np.min(X))
    print("X max:", np.max(X))

    # split train and val
    X_val, X_train = X[0:NB_VALIDATION, ...], X[NB_VALIDATION:, ...]
    y_val, y_train = y[0:NB_VALIDATION, ...], y[NB_VALIDATION:, ...]
    print("%d of %d values in y_train are 1, %d of %d values in y_val" % (np.count_nonzero(y_train), y_train.shape[0], np.count_nonzero(y_val), y_val.shape[0]))
    print(X_train.shape, X_val.shape)
    print(y_train.shape, y_val.shape)

    print("Training...")
    svc = SVC(C=0.001)
    svc.fit(X_train, y_train)

    print("Predictions...")
    preds = svc.predict(X_val)
    for i in range(preds.shape[0]):
        print(i, preds[i])

    print("Scoring...")
    acc = svc.score(X_val, y_val)
    print("accuracy = %.4f" % (acc))

def load_xy(dataset, nb_crops_max, nb_augmentations):
    X = []
    y = []

    examples = get_crops_with_labels(dataset, nb_crops_max, nb_augmentations,
                                     model_image_height=MODEL_IMAGE_HEIGHT,
                                     model_image_width=MODEL_IMAGE_WIDTH,
                                     crop_height=CROP_HEIGHT, crop_width=CROP_WIDTH)

    for i, (crop, face_factor) in enumerate(examples):
        if i % 100 == 0:
            print("Crop %d of %d" % (i+1, nb_crops_max))

        distances = [1, 3, 5, 7]
        angles = [0*np.pi/3, 1*np.pi/3, 2*np.pi/3, 3*np.pi/3]
        glcm = greycomatrix(crop, distances, angles, 256, symmetric=True, normed=True)
        dissimilarities = greycoprops(glcm, 'dissimilarity')
        energies = greycoprops(glcm, 'energy')
        correlations = greycoprops(glcm, 'correlation')

        nb_matrices = len(distances) * len(angles)
        all_values = np.zeros((3*nb_matrices))
        all_values[0:nb_matrices] = dissimilarities.flatten()
        all_values[nb_matrices:nb_matrices*2] = energies.flatten()
        all_values[nb_matrices*2:nb_matrices*3] = correlations.flatten()

        is_cat = True if face_factor >= CAT_FRACTION_THRESHOLD else False
        #if is_cat or random.random() < 0.25:
        X.append(all_values)
        y.append(1 if is_cat else 0)

    # all entries in X/Y same length
    assert len(set([len(row) for row in X])) == 1
    #assert len(set([len(row) for row in y])) == 1

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.float32)

    return X, y

if __name__ == "__main__":
    main()
