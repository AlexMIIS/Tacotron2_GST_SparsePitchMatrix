######################################################################################################
# The main script where the data preparation, training and evaluation happens.
######################################################################################################

import torch
from torch.utils.data import DataLoader
from torch.utils.data.distributed import DistributedSampler

from hyper_parameters import tacotron_params
from data_preparation import DataPreparation, DataCollate
from training import train

if __name__ == '__main__':
    # run()
    # ---------------------------------------- DEFINING INPUT ARGUMENTS ---------------------------------------------- #

    training_files = 'filelists/ljs_audio_text_train_filelist.txt'
    validation_files = 'filelists/ljs_audio_text_val_filelist.txt'

    # GST Prosody features:
    training_prosody_features_path = '/training_prosody_features/'
    validation_prosody_features_path = '/validation_prosody_features/'

    output_directory = '/outputs'
    log_directory = '/loggs'
    checkpoint_path = '/outputs/checkpoint_62000'
    # checkpoint_path = None
    warm_start = False
    n_gpus = 1
    rank = 0

    torch.backends.cudnn.enabled = tacotron_params['cudnn_enabled']
    torch.backends.cudnn.benchmark = tacotron_params['cudnn_benchmark']

    print("FP16 Run:", tacotron_params['fp16_run'])
    print("Dynamic Loss Scaling:", tacotron_params['dynamic_loss_scaling'])
    print("Distributed Run:", tacotron_params['distributed_run'])
    print("CUDNN Enabled:", tacotron_params['cudnn_enabled'])
    print("CUDNN Benchmark:", tacotron_params['cudnn_benchmark'])

    # --------------------------------------------- PREPARING DATA --------------------------------------------------- #

    # Read the training files
    with open(training_files, encoding='utf-8') as f:
        training_audiopaths_and_text = [line.strip().split("|") for line in f]

    # Read the validation files
    with open(validation_files, encoding='utf-8') as f:
        validation_audiopaths_and_text = [line.strip().split("|") for line in f]

    train_data = DataPreparation(training_audiopaths_and_text, training_prosody_features_path, tacotron_params)
    validation_data = DataPreparation(validation_audiopaths_and_text, validation_prosody_features_path, tacotron_params)
    collate_fn = DataCollate(tacotron_params['number_frames_step'])

    train_sampler = DistributedSampler(train_data) if tacotron_params['distributed_run'] else None
    val_sampler = DistributedSampler(validation_data) if tacotron_params['distributed_run'] else None

    train_loader = DataLoader(train_data, num_workers=1, shuffle=False, sampler=train_sampler,
                              batch_size=tacotron_params['batch_size'], pin_memory=False, drop_last=True,
                              collate_fn=collate_fn)

    validate_loader = DataLoader(validation_data, num_workers=1, shuffle=False, sampler=val_sampler,
                                 batch_size=tacotron_params['batch_size'], pin_memory=False, drop_last=True,
                                 collate_fn=collate_fn)

    # ------------------------------------------------- TRAIN -------------------------------------------------------- #

    train(output_directory, log_directory, checkpoint_path, warm_start, n_gpus, rank, hyper_params=tacotron_params,
          valset=validation_data, collate_fn=collate_fn, train_loader=train_loader, group_name="group_name")

    print("Training completed")
