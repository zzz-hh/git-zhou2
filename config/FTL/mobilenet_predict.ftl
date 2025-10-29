{
	"roles": {
		"client": "Bob"
	},
	"common_params": {
		"model": "${model}",
		"process": "predict",
		"task_name": "HFL_MobileNet_multiclass_predict",
		"resize": ${resize}
	},
	"role_params": {
	    "Bob": {
          "data_set": "${label_dataset}",
          "model_path": "${hostModelFileName}",
          "predict_path": "${predictFileName}"
        }
	}
}