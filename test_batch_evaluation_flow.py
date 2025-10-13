"""
批量评估流程测试脚本

功能：
1. 模拟前端批量评估流程
2. 测试多个RAG技术的评估
3. 展示统计对比功能

使用方法：
    python test_batch_evaluation_flow.py
"""

import requests
import time
import json
from typing import List, Dict, Any


API_BASE_URL = "http://localhost:8000/api/v1"


def test_batch_evaluation_flow():
    """测试批量评估完整流程"""
    
    print("=" * 80)
    print("🚀 批量评估流程测试")
    print("=" * 80)
    print()
    
    # 步骤1: 查询多个RAG技术
    print("📝 步骤1: 执行RAG查询")
    print("-" * 80)
    
    query_request = {
        "query": "什么是RAG技术？",
        "document_ids": [1],  # 假设文档ID为1
        "rag_techniques": [
            "simple_rag",
            "reranker_rag",
            "fusion_rag",
            "hyde_rag",
        ],
        "session_id": None,
        "llm_config": {"temperature": 0.7},
        "rag_config": {"top_k": 5}
    }
    
    try:
        print(f"📤 发送查询: {query_request['query']}")
        print(f"🎯 选择RAG技术: {', '.join(query_request['rag_techniques'])}")
        print()
        
        response = requests.post(
            f"{API_BASE_URL}/qa/query",
            json=query_request,
            timeout=120
        )
        
        if response.status_code != 200:
            print(f"❌ 查询失败: {response.status_code}")
            print(response.text)
            return
        
        results = response.json()
        print(f"✅ 查询成功! 获得 {len(results)} 个RAG结果")
        print()
        
        # 提取qa_record_id
        qa_record_ids = []
        for i, result in enumerate(results):
            technique = result.get("rag_technique")
            qa_id = result.get("qa_record_id")
            exec_time = result.get("execution_time", 0)
            
            print(f"  {i+1}. {technique:30s} - 耗时: {exec_time:.2f}秒, QA_ID: {qa_id}")
            
            if qa_id:
                qa_record_ids.append(qa_id)
        
        print()
        
        if not qa_record_ids:
            print("❌ 未获取到qa_record_id，无法继续评估")
            return
        
        # 步骤2: 批量自动评估
        print("=" * 80)
        print("🤖 步骤2: 批量自动评估")
        print("-" * 80)
        print()
        
        eval_results = []
        
        for i, qa_id in enumerate(qa_record_ids):
            technique = results[i]["rag_technique"]
            print(f"⏳ 评估中 [{i+1}/{len(qa_record_ids)}]: {technique}")
            
            eval_request = {
                "qa_record_id": qa_id,
                "use_llm_evaluator": True,
                "use_ragas": False,  # 快速测试，不使用Ragas
                "reference_answer": None
            }
            
            try:
                eval_response = requests.post(
                    f"{API_BASE_URL}/evaluation/auto",
                    json=eval_request,
                    timeout=120
                )
                
                if eval_response.status_code == 200:
                    eval_data = eval_response.json()
                    
                    if eval_data.get("evaluation_success"):
                        eval_results.append({
                            "technique": technique,
                            "qa_id": qa_id,
                            "eval_data": eval_data,
                            "exec_time": results[i]["execution_time"]
                        })
                        
                        llm_eval = eval_data.get("llm_evaluation", {})
                        overall = llm_eval.get("overall_score", 0)
                        print(f"  ✅ 综合得分: {overall:.1f}/10")
                    else:
                        print(f"  ⚠️ 评估失败")
                else:
                    print(f"  ❌ API错误: {eval_response.status_code}")
            
            except Exception as e:
                print(f"  ❌ 评估出错: {str(e)}")
            
            print()
            time.sleep(0.5)  # 避免请求过快
        
        # 步骤3: 展示统计对比
        print("=" * 80)
        print("📊 步骤3: 统计对比结果")
        print("=" * 80)
        print()
        
        if not eval_results:
            print("❌ 无可用的评估结果")
            return
        
        # 构建对比表格
        print("📋 详细对比表:")
        print("-" * 100)
        header = f"{'RAG技术':<30s} {'执行时间':<12s} {'相关性':<8s} {'忠实度':<8s} {'连贯性':<8s} {'流畅度':<8s} {'简洁性':<8s} {'综合得分':<10s}"
        print(header)
        print("-" * 100)
        
        comparison_data = []
        
        for result in eval_results:
            technique = result["technique"]
            exec_time = result["exec_time"]
            llm_eval = result["eval_data"].get("llm_evaluation", {})
            
            relevance = llm_eval.get("relevance_score", 0)
            faithfulness = llm_eval.get("faithfulness_score", 0)
            coherence = llm_eval.get("coherence_score", 0)
            fluency = llm_eval.get("fluency_score", 0)
            conciseness = llm_eval.get("conciseness_score", 0)
            overall = llm_eval.get("overall_score", 0)
            
            row = f"{technique:<30s} {exec_time:<12.2f} {relevance:<8.1f} {faithfulness:<8.1f} {coherence:<8.1f} {fluency:<8.1f} {conciseness:<8.1f} {overall:<10.1f}"
            print(row)
            
            comparison_data.append({
                "technique": technique,
                "exec_time": exec_time,
                "overall": overall,
                "relevance": relevance,
                "faithfulness": faithfulness,
                "coherence": coherence,
                "fluency": fluency,
                "conciseness": conciseness
            })
        
        print("-" * 100)
        print()
        
        # 排名
        print("🏆 综合排名:")
        print("-" * 80)
        
        sorted_by_score = sorted(comparison_data, key=lambda x: x["overall"], reverse=True)
        
        medals = ["🥇", "🥈", "🥉"]
        for i, data in enumerate(sorted_by_score[:3]):
            medal = medals[i] if i < 3 else f"  {i+1}."
            print(f"{medal} {data['technique']:30s} - 得分: {data['overall']:5.1f}/10, 耗时: {data['exec_time']:5.2f}秒")
        
        print()
        
        # 最快RAG
        fastest = min(comparison_data, key=lambda x: x["exec_time"])
        print(f"⚡ 最快RAG: {fastest['technique']} ({fastest['exec_time']:.2f}秒)")
        print()
        
        # 各维度最优
        print("🎯 各维度最优:")
        print("-" * 80)
        
        dimensions = [
            ("相关性", "relevance"),
            ("忠实度", "faithfulness"),
            ("连贯性", "coherence"),
            ("流畅度", "fluency"),
            ("简洁性", "conciseness")
        ]
        
        for dim_name, dim_key in dimensions:
            best = max(comparison_data, key=lambda x: x[dim_key])
            print(f"  • {dim_name:8s}: {best['technique']:30s} ({best[dim_key]:.1f}分)")
        
        print()
        
        # 综合分析
        print("=" * 80)
        print("💡 综合分析与推荐")
        print("=" * 80)
        print()
        
        best_technique = sorted_by_score[0]
        
        print(f"🏆 最佳综合表现: {best_technique['technique']}")
        print(f"   - 综合得分: {best_technique['overall']:.1f}/10")
        print(f"   - 执行时间: {best_technique['exec_time']:.2f}秒")
        print(f"   - 相关性: {best_technique['relevance']:.1f}, 忠实度: {best_technique['faithfulness']:.1f}")
        print()
        
        # 平衡推荐
        efficiency_scores = [
            {
                "technique": d["technique"],
                "score": d["overall"],
                "time": d["exec_time"],
                "efficiency": d["overall"] / d["exec_time"]  # 得分/时间 = 效率
            }
            for d in comparison_data
        ]
        
        best_efficiency = max(efficiency_scores, key=lambda x: x["efficiency"])
        print(f"⚡ 最佳效率: {best_efficiency['technique']}")
        print(f"   - 效率值: {best_efficiency['efficiency']:.2f} (得分/秒)")
        print(f"   - 综合得分: {best_efficiency['score']:.1f}/10")
        print(f"   - 执行时间: {best_efficiency['time']:.2f}秒")
        print()
        
        print("=" * 80)
        print("✅ 批量评估流程测试完成!")
        print("=" * 80)
        
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败: 请确保后端服务已启动 (http://localhost:8000)")
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print()
    print("🔧 批量评估流程测试脚本")
    print("📝 确保后端服务已启动: python backend/main.py")
    print("📝 确保已上传至少一个文档")
    print()
    input("按Enter键开始测试...")
    print()
    
    test_batch_evaluation_flow()

