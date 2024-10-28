#!/usr/bin/env python3
# @brief:    Training script for range image-based point cloud prediction
# @author    Benedikt Mersch    [mersch@igg.uni-bonn.de

import os
import time
import argparse
import yaml

import lightning.pytorch as pl
from lightning.pytorch import Trainer, seed_everything
from lightning.pytorch.loggers import TensorBoardLogger
from lightning.pytorch.callbacks import LearningRateMonitor, ModelCheckpoint
from lightning.pytorch.callbacks.early_stopping import EarlyStopping
from lightning.pytorch.strategies.ddp import DDPStrategy

import subprocess
import sys
from datasets.datasets import KittiOdometryModule
from datasets.datasets_nuscenes import NuScenesModule
from models.models import Model1, Model2

if __name__ == "__main__":
    parser = argparse.ArgumentParser("./run.py")
    parser.add_argument(
        "--comment", "-c", type=str, default="", help="Add a comment to the LOG ID."
    )
    parser.add_argument(
        "--processeddatapath", "-pdp", type=str, default="", help="Path to the processed dataset"
    )
    parser.add_argument(
        "--test", "-t", type=str, default=None, help="Evaluate the model: Specify model path to evaluate."
    )
    parser.add_argument(
        "--model", "-mo", type=str, default="model1", help="Choose which model to use for run: model1 or model2"
    )
    parser.add_argument(
        "--dataset", "-d", type=str, default="kitti", help="Specify which dataset to run for."
    )
    parser.add_argument(
        "-res",
        "--resume",
        type=str,
        default=None,
        help="Resume training from specified model.",
    )
    parser.add_argument(
        "-w",
        "--weights",
        type=str,
        default=None,
        help="Init model with weights from specified model",
    )
    parser.add_argument(
        "-r",
        "--range",
        type=float,
        default=None,
        help="Change weight of range image loss.",
    )
    parser.add_argument(
        "-m", "--mask", type=float, default=None, help="Change weight of mask loss."
    )
    parser.add_argument(
        "-cd",
        "--chamfer",
        type=float,
        default=None,
        help="Change weight of Chamfer distance loss.",
    )
    parser.add_argument(
        "-e", "--epochs", type=int, default=None, help="Number of training epochs."
    )
    parser.add_argument(
        "-seq",
        "--sequence",
        type=int,
        nargs="+",
        default=None,
        help="Sequences for training.",
    )
    args, unparsed = parser.parse_known_args()

    model_path = args.resume if args.resume else args.weights
    test = args.test
    dataset = args.dataset

    if model_path:
        ###### Load config and update parameters
        checkpoint_path = model_path
        config_filename = "./config/parameters.yml" if dataset=="kitti" else "./config/nuscenes_parameters.yml"
        cfg = yaml.safe_load(open(config_filename))

        if args.weights and not args.comment:
            args.comment = "_pretrained"

        cfg["GIT_COMMIT_VERSION"] = 'none'
        if args.comment:
            cfg["EXPERIMENT"]["ID"] = args.comment
        cfg["LOG_NAME"] = cfg["EXPERIMENT"]["ID"] + "_" + time.strftime("%Y%m%d_%H%M%S")
        cfg["LOG_DIR"] = os.path.join(
            "./runs", cfg["GIT_COMMIT_VERSION"], cfg["LOG_NAME"]
        )
        if not os.path.exists(cfg["LOG_DIR"]):
            os.makedirs(cfg["LOG_DIR"], exist_ok=True)
        print("Starting experiment in log dir:", cfg["LOG_DIR"])

        """Manually set these"""
        cfg["DATA_CONFIG"]["COMPUTE_MEAN_AND_STD"] = False
        cfg["DATA_CONFIG"]["GENERATE_FILES"] = False

        if args.epochs:
            cfg["TRAIN"]["MAX_EPOCH"] = args.epochs
            print("Set max_epochs to ", args.epochs)
        if args.range:
            cfg["TRAIN"]["LOSS_WEIGHT_RANGE_VIEW"] = args.range
            print("Overwriting LOSS_WEIGHT_RANGE_VIEW =", args.range)
        if args.mask:
            cfg["TRAIN"]["LOSS_WEIGHT_MASK"] = args.mask
            print("Overwriting LOSS_WEIGHT_MASK =", args.mask)
        if args.chamfer:
            cfg["TRAIN"]["LOSS_WEIGHT_CHAMFER_DISTANCE"] = args.chamfer
            print("Overwriting LOSS_WEIGHT_CHAMFER_DISTANCE =", args.chamfer)
        if args.sequence:
            cfg["DATA_CONFIG"]["SPLIT"]["TRAIN"] = args.sequence
            print("Training on sequences ", args.sequence)
    else:
        ###### Create new log
        resume_from_checkpoint = None
        config_filename = "./config/parameters.yml" if dataset=="kitti" else "./config/nuscenes_parameters.yml"
        cfg = yaml.safe_load(open(config_filename))
        # cfg["GIT_COMMIT_VERSION"] = str(
        #     subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).strip()
        # ).split("'")[1]
        cfg["GIT_COMMIT_VERSION"] = 'none'
        if args.comment:
            cfg["EXPERIMENT"]["ID"] = args.comment
        cfg["LOG_NAME"] = cfg["EXPERIMENT"]["ID"] + "_" + time.strftime("%Y%m%d_%H%M%S")
        cfg["LOG_DIR"] = os.path.join(
            "./runs", cfg["GIT_COMMIT_VERSION"], cfg["LOG_NAME"]
        )
        if not os.path.exists(cfg["LOG_DIR"]):
            os.makedirs(cfg["LOG_DIR"], exist_ok=True)
        print("Starting experiment in log dir:", cfg["LOG_DIR"])

    ###### Logger
    tb_logger = TensorBoardLogger(
        save_dir=cfg["LOG_DIR"], default_hp_metric=False, name="", version=""
    )
    seed_everything(cfg["EXPERIMENT"]["SEED"], workers=True)

    ###### Dataset
    cfg["DATA_CONFIG"]["PROCESSED_PATH"] = args.processeddatapath
    data = KittiOdometryModule(cfg) if dataset=="kitti" else NuScenesModule(cfg)
    data.setup()
    print("data setup done")

    ###### Model
    input_shape = (5,1,64,2048) if dataset=="kitti" else (5,1,32,1024)
    model = Model1(cfg, input_shape) if args.model=="model1" else Model2(cfg, input_shape)

    ###### Load checkpoint
    if args.resume:
        resume_from_checkpoint = checkpoint_path
        print("Resuming from checkpoint ", checkpoint_path)
    elif args.weights:
        model = model.load_from_checkpoint(checkpoint_path, cfg=cfg,\
                num_channels=1, num_kernels=32,\
                kernel_size=(3, 3), padding=(1, 1), activation="relu",\
                img_size=(64, 64), num_layers=3, peep=False)
        resume_from_checkpoint = None
        print("Loading weights from ", checkpoint_path)

    ###### Callbacks
    lr_monitor = LearningRateMonitor(logging_interval="step")
    checkpoint = ModelCheckpoint(
        monitor="val/loss",
        dirpath=os.path.join(cfg["LOG_DIR"], "checkpoints"),
        filename="min_val_loss",
        mode="min",
        save_last=True,
        verbose=True
    )
    early_stop = EarlyStopping(monitor="val/loss", mode="min",
            verbose=True, patience=10)

    ###### Trainer
    trainer = Trainer(
        accelerator="cuda",
        devices=1,
        num_nodes=1,
        logger=tb_logger,
        accumulate_grad_batches=cfg["TRAIN"]["BATCH_ACC"], # times accumulate_grad_batches
        max_epochs=cfg["TRAIN"]["MAX_EPOCH"],
        log_every_n_steps=cfg["TRAIN"]["LOG_EVERY_N_STEPS"],
        callbacks=[lr_monitor, checkpoint],
        check_val_every_n_epoch=1,
        limit_train_batches=1.0,
        limit_val_batches=1.0,
        limit_test_batches=1.0
    )

    ###### Training
    if not args.test:
        trainer.fit(model, data, ckpt_path=resume_from_checkpoint)
        print("Finished Training> Starting Test.")
    ###### Testing
    if args.test:
        checkpoint_path = args.test
    else:
        checkpoint_path = cfg["LOG_DIR"] + "/checkpoints/min_val_loss.ckpt"
    
    results = trainer.test(model, data.test_dataloader(), ckpt_path=checkpoint_path)

    if tb_logger:
        filename = os.path.join(
            cfg["LOG_DIR"], "test", "results_" + time.strftime("%Y%m%d_%H%M%S") + ".yml"
        )
        log_to_save = {**{"results": results}, **vars(args), **cfg}
        with open(filename, "w") as yaml_file:
            yaml.dump(log_to_save, yaml_file, default_flow_style=False)