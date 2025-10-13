"""
自动评估功能测试脚本
"""
import requests
import json
import time
from typing import List, Dict

API_BASE_URL = "http://localhost:8000/api/v1"


def print_separator(title=""):
    """打印分隔线"""
    print("\n" + "=" * 80)
    if title:
        print(f"  {title}")
        print("=" * 80)


def test_auto_evaluation(qa_record_id: int, use_ragas: bool = False):
    """测试单条自动评估"""
    print_separator(f"自动评估 QA记录 {qa_record_id}")
    
    payload = {
        "qa_record_id": qa_record_id,
        "use_llm_evaluator": True,
        "use_ragas": use_ragas,
        "reference_answer": None  # 可选的参考答案
    }
    
    print(f"请求配置:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/evaluation/auto",
            json=payload,
            timeout=120
        )
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n✅ 评估成功! 耗时: {elapsed_time:.2f}秒")
            print(f"\n评估时间: {result.get('evaluation_time', 0):.2f}秒")
            
            # LLM评估结果
            if result.get("llm_evaluation"):
                print("\n--- LLM评估结果 ---")
                llm_eval = result["llm_evaluation"]
                print(f"相关性: {llm_eval.get('relevance_score', 0):.2f}/10")
                print(f"忠实度: {llm_eval.get('faithfulness_score', 0):.2f}/10")
                print(f"连贯性: {llm_eval.get('coherence_score', 0):.2f}/10")
                print(f"流畅度: {llm_eval.get('fluency_score', 0):.2f}/10")
                print(f"简洁性: {llm_eval.get('conciseness_score', 0):.2f}/10")
                print(f"综合得分: {llm_eval.get('overall_score', 0):.2f}/10")
                print(f"反馈: {llm_eval.get('feedback', '')}")
            
            # Ragas评估结果
            if result.get("ragas_evaluation") and result["ragas_evaluation"].get("ragas_available"):
                print("\n--- Ragas评估结果 ---")
                ragas_eval = result["ragas_evaluation"]
                if ragas_eval.get("evaluation_success"):
                    scores = ragas_eval.get("scores", {})
                    print(f"Faithfulness: {scores.get('faithfulness', 0):.3f}")
                    print(f"Answer Relevancy: {scores.get('answer_relevancy', 0):.3f}")
                    print(f"Context Precision: {scores.get('context_precision', 0):.3f}")
                    print(f"Context Recall: {scores.get('context_recall', 0):.3f}")
                    print(f"平均分: {ragas_eval.get('average_score', 0):.3f}")
                else:
                    print(f"❌ Ragas评估失败: {ragas_eval.get('error', '')}")
            
            # 综合评分
            print("\n--- 综合评分 ---")
            final_scores = result.get("final_scores", {})
            for key, value in final_scores.items():
                print(f"{key}: {value:.3f}")
            
            return result
        else:
            print(f"\n❌ 失败! 状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"\n⏰ 请求超时 (>120秒)")
        return None
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        return None


def test_batch_evaluation(qa_record_ids: List[int]):
    """测试批量评估"""
    print_separator(f"批量评估 {len(qa_record_ids)} 条记录")
    
    payload = {
        "qa_record_ids": qa_record_ids,
        "use_llm_evaluator": True,
        "use_ragas": False  # 批量评估时可以关闭Ragas加速
    }
    
    print(f"待评估记录: {qa_record_ids}")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/evaluation/auto/batch",
            json=payload,
            timeout=300
        )
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n✅ 批量评估完成! 总耗时: {elapsed_time:.2f}秒")
            print(f"\n总数: {result['total_count']}")
            print(f"成功: {result['success_count']}")
            print(f"失败: {result['failed_count']}")
            print(f"评估时间: {result['total_time']:.2f}秒")
            
            # 显示每条记录的综合得分
            print("\n--- 各记录综合得分 ---")
            print(f"{'QA记录ID':<12} {'综合得分':<12} {'状态'}")
            print("-" * 40)
            for res in result['results']:
                qa_id = res['qa_record_id']
                overall_score = res['final_scores'].get('overall_score', 0)
                status = "✅" if res['evaluation_success'] else "❌"
                print(f"{qa_id:<12} {overall_score:<12.2f} {status}")
            
            return result
        else:
            print(f"\n❌ 失败! 状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"\n⏰ 请求超时 (>300秒)")
        return None
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        return None


def get_recent_qa_records(limit: int = 10) -> List[int]:
    """获取最近的QA记录ID"""
    try:
        # 这里需要实现获取QA记录的API
        # 暂时返回示例ID
        print(f"\n获取最近{limit}条QA记录...")
        print("⚠️ 请手动替换为实际的QA记录ID")
        return [1, 2, 3]  # 示例ID，需要替换
    except Exception as e:
        print(f"获取QA记录失败: {e}")
        return []


def main():
    """主测试函数"""
    print_separator("自动评估功能测试")
    print("\n确保后端服务已启动: python backend/main.py")
    print("确保已经有QA记录数据")
    
    input("\n按Enter键开始测试...")
    
    # 测试1: 单条评估（仅LLM）
    print_separator("测试1: 单条评估（LLM评分器）")
    test_auto_evaluation(qa_record_id=1, use_ragas=False)
    time.sleep(2)
    
    # 测试2: 单条评估（LLM + Ragas）
    print_separator("测试2: 单条评估（LLM + Ragas）")
    print("注意: Ragas评估可能需要更长时间")
    test_auto_evaluation(qa_record_id=1, use_ragas=True)
    time.sleep(2)
    
    # 测试3: 批量评估
    print_separator("测试3: 批量评估")
    qa_ids = get_recent_qa_records(limit=5)
    if qa_ids:
        test_batch_evaluation(qa_ids)
    else:
        print("⚠️ 没有可评估的QA记录")
    
    # 测试4: 查看评估统计
    print_separator("测试4: 查看评估统计")
    try:
        response = requests.get(f"{API_BASE_URL}/evaluation/stats/comparison")
        if response.status_code == 200:
            stats = response.json()
            print("\n--- RAG技术对比统计 ---")
            print(f"{'技术':<30} {'查询数':<10} {'平均得分':<12} {'平均耗时'}")
            print("-" * 70)
            for stat in stats:
                print(f"{stat['technique']:<30} "
                      f"{stat['total_queries']:<10} "
                      f"{stat['avg_overall_score']:<12.2f} "
                      f"{stat['avg_execution_time']:.3f}s")
        else:
            print(f"获取统计失败: {response.status_code}")
    except Exception as e:
        print(f"获取统计失败: {e}")
    
    # 总结
    print_separator("测试完成")
    print("\n✅ 所有测试已完成！")
    print("\n📊 功能说明:")
    print("1. LLM评分器: 使用qwen-plus进行5维度评分")
    print("   - 相关性、忠实度、连贯性、流畅度、简洁性")
    print("\n2. Ragas评估: 标准化RAG评估指标")
    print("   - Faithfulness, Answer Relevancy, Context Precision/Recall")
    print("\n3. 批量评估: 一次评估多条QA记录")
    print("\n4. 自动保存: 评估结果自动保存到数据库")
    print("\n💡 提示:")
    print("- 单条评估（LLM）约5-10秒")
    print("- 单条评估（LLM+Ragas）约15-30秒")
    print("- 批量评估可显著节省时间")
    print("- 查看后端日志了解详细评估过程")


if __name__ == "__main__":
    main()

