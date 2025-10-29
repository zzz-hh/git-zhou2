{
	"roles": {
		"client": "Bob"
	},
	"common_params": {
		"model": "${model}",
		"process": "predict",
		"task_name": "SVM_plaintext_prdict"
	},
	"role_params": {
	    "Bob": {
          "data_set": "${label_dataset}",
          "model_path": "${hostModelFileName}",
          "predict_path": "${predictFileName}"
        }
	}
}