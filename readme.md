# Accurate and Real-Time LiDAR Point Cloud Forecasting For Autonomous Driving

## 1. Clone the repository
Clone this repository along with its submodules
```
git clone --recurse-submodules https://github.com/lighterbird/Accurate-and-Real-Time-LiDAR-Point-Cloud-Forecasting-For-Autonomous-Driving.git
```

## 2. Setup the dependencies
All the required dependencies are specified in the `environment_setup.yml` file.  
In order to create a conda environment use command: 

```
conda env create -f environment_setup.yml
```

## 3. Run the code
All the required code for preprocessing the dataset, training and evaluation is given in `preprocess.py` and `run.py`  

### 1. Data preprocessing
In order to preprocess your data (ie- convert point clouds to range images in required format) run `preprocess.py` with the following arguments:  

```
python preprocess.py --dataset "" --dataset_path "" --processed_path ""
```  
1. `--dataset` can take values `"kitti"` or `"nuscenes"`
2. `--dataset_path` is the path to your raw dataset folder
3. `--processed_path` is the path to save the processed dataset at

### 2. Training
In order to train the model run `run.py` with the following arguments  

```
python run.py --dataset "" --processeddatapath "" --model "" 
```
1. `--dataset` can take values `"kitti"` or `"nuscenes"`
2. `--processeddatapath` is the path to the processed dataset folder
3. `--model` can take values `"model1"` or `"model2"`

### 3. Evaluation
Following is the link to the trained checkpoints for both model1 and model2 on both kitti and nuscenes dataset:  

[Link to Checkpoints](https://drive.google.com/drive/folders/0BxAelcIYrKLMflBUTDdQLUNMRUM3cEJBVmw1ZjRFeFM4NTFqeGQ3MUxZS01KeWpwWnFQU1U?resourcekey=0-cmLjTZXl4tGQi60484uzCw&usp=drive_link)


To evaluate a model on a dataset, run `run.py` with the following arguments  

```

python run.py --test "" --dataset "" --processeddatapath "" --model "" 
```
1. `--test` specifies the path to the trained model which is to be evaluated
2. `--dataset` can take values `"kitti"` or `"nuscenes"`
3. `--processeddatapath` is the path to the processed dataset folder
4. `--model` can take values `"model1"` or `"model2"`
