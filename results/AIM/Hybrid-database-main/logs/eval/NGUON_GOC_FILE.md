# Nguồn gốc các file trong thư mục kết quả grounding

Phiên Kaggle (notebook `eval_grounding_kaggle.ipynb`, manifest 2026-10-15T08:56:38) bị dừng ở giới hạn 12 giờ khi đã sinh
1.913/1.916 mục và chưa chấm. Phần còn lại chạy ở máy local (cùng code, cùng 3 model Ollama cùng digest, Ollama 0.40.3,
PostgreSQL local đã kiểm: 400 món, 14 dòng map, 10 CBT, 988 embedding, 384 tổ hợp state khớp bản JSON).

| File | Nguồn |
|---|---|
| grounding/A_*_replies.jsonl, B_B1/B2/B3_runs.jsonl | Kaggle |
| grounding/B_B4_runs_kaggle_237.jsonl | Kaggle (237 hội thoại, bản gốc khi bị dừng) |
| grounding/B_B4_runs.jsonl | 237 dòng đầu giống hệt bản Kaggle + 3 hội thoại B4_238–240 sinh ở local |
| grounding/*_scored.jsonl | Chấm ở local (giám khảo gemma3:4b, digest 68ceab7e468a) |
| run_grounding_gen_a.txt, run_grounding_gen_b.txt | Log Kaggle |
| run_grounding_gen_b_local.txt, run_grounding_score_local.txt, run_grounding_report.txt | Log local |
| run_judge_consistency.txt, judge_consistency.json | Kiểm độ nhất quán giám khảo Kaggle vs local: 99/100 ca safety cùng kết quả |
| ../turns.jsonl | Trace từng lượt của pipeline: 1.418 dòng từ Kaggle + 3 dòng của B4_238–240 chạy ở local (câu trả lời trong trace khớp với B_B4_runs.jsonl) |
| ../turns_kaggle.jsonl | Bản trace gốc từ Kaggle (1.418 dòng) |
| results/hlamonhaylafinalh.log, results/ollama.log, results/seed.log | Log notebook, Ollama và seed trên Kaggle |
