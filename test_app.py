import unittest

import pandas as pd

import app


class SurveyAnalysisAppTest(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame(
            {
                "部門": ["営業", "営業", "企画"],
                "職位": ["一般", "管理職", "一般"],
                "性別": ["女性", "男性", "女性"],
                "年代": ["20代", "30代", "20代"],
                "採用区分": ["新卒", "中途", "新卒"],
                "研修の必要度": ["必要性を感じる", "強く必要性を感じる", "必要性を感じる"],
                "研修内容のレベル": ["ちょうどいい", "難しい", "やさしい"],
                "研修の有用度": ["今後役立つものである", "普通", "今後役立つものである"],
                "講師評価": ["4", "5", "4"],
                "研修時間": ["ちょうどいい", "長い", "ちょうどいい"],
                "研修の満足度": ["5", "4", "5"],
                "研修内容の活用有無": ["活用した", "活用していない", "活用した"],
                "結果の内容": [
                    "とても有用でした。改善点も少なく、満足しています。",
                    "時間がないです。改善が必要です。",
                    "良い研修でした。役立ちました。",
                ],
            }
        )

    def test_summarize_question_mean(self):
        result = app.summarize_question(self.df, "研修の必要度")
        self.assertEqual(result["count"], 3)
        self.assertAlmostEqual(result["mean"], 4.33, places=2)

    def test_summarize_freetext_categories(self):
        result = app.summarize_freetext(self.df)
        self.assertGreater(result["ポジティブ"], 0)
        self.assertGreater(result["ネガティブ"], 0)
        self.assertGreater(result["items"].__len__(), 0)

    def test_build_markdown_report(self):
        report = app.build_markdown_report(self.df)
        self.assertIn("アンケート分析レポート", report)
        self.assertIn("自由記述分析", report)


if __name__ == "__main__":
    unittest.main()
