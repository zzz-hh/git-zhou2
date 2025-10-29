{
	"roles": {
		"server": "Alice",
		"client": [
			"Bob",
			"Charlie"
		]
	},
	"common_params": {
		"model": "${model}",
		"method": "${encryption!"Plaintext"}",
		"process": "train",
		"task_name": "HFL_ResNet_multiclass_plaintext_train",
		"learning_rate": ${learningRate!0.1},
		"optimizer": ${optimizer},
		"alpha": ${alpha!0.0001},
		"batch_size": ${batchSize!100},
		"global_epoch": ${globalEpoch!100},
		"local_epoch": ${localEpoch!1},
		"print_metrics": ${printMetrics!false?c}
		"resize": ${resize}
	},
	"role_params": {
		"Bob": {
			"data_set": "${label_dataset}",
			"model_path": "${hostModelFileName}",
			"metric_path": "${indicatorFileName}"
		},
		"Charlie": {
			"data_set": "${guest_dataset}",
			"model_path": "${guestModelFileName}",
			"metric_path": "${indicatorFileName}"
		},
		"Alice": {
			"data_set": "${arbiter_dataset}",
			"metric_path": "/data${indicatorFileName}"
		}
	}
}