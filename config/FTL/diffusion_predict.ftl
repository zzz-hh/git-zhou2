{
	"roles": {
		"client": "Bob"
	},
	"common_params": {
		"model": "${model}",
		"process": "predict",
		"task_name": "minidiffusion_plaintext_prdict",
		"model_ema_steps": 10,
        "n_samples": 36,
        "no_clip": 0,
        "save_dir": "result",
        "model_ema_decay": 0.995
	},
	"role_params": {
	    "Bob": {
          "data_set": "${label_dataset}",
          "model_path": "${hostModelFileName}",
          "predict_path": "${predictFileName}"
        }
	}
}