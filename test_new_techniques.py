"""
测试新增的3个RAG技术
"""
import requests
import json
import time

API_BASE_URL = "http://localhost:8000/api/v1"

def print_separator(title=""):
    print("\n" + "=" * 80)
    if title:
        print(f"  {title}")
        print("=" * 80)

def test_query(technique_name, query, rag_config=None):
    """测试单个RAG技术"""
    print_separator(f"测试: {technique_name}")
    print(f"查询: {query}")
    
    payload = {
        "query": query,
        "rag_techniques": [technique_name],
        "rag_config": rag_config or {},
        "top_k": 3
    }
    
    print(f"\n请求配置:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/qa/query",
            json=payload,
            timeout=60
        )
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n✅ 成功! 耗时: {elapsed_time:.2f}秒")
            print(f"\n会话ID: {result.get('session_id')}")
            
            # 显示结果
            if 'results' in result and result['results']:
                for rag_result in result['results']:
                    print(f"\n--- {rag_result['rag_technique']} ---")
                    print(f"答案:\n{rag_result['answer'][:500]}...")
                    print(f"\n检索到的文档数: {len(rag_result['retrieved_docs'])}")
                    if rag_result['retrieved_docs']:
                        print(f"最高相似度: {rag_result['retrieved_docs'][0]['score']:.4f}")
            else:
                print("\n⚠️ 没有返回结果")
                
        else:
            print(f"\n❌ 失败! 状态码: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except requests.exceptions.Timeout:
        print(f"\n⏰ 请求超时 (>60秒)")
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")


def main():
    """主测试函数"""
    print_separator("RAG技术测试 - 新增3个高级技术")
    print("\n确保后端服务已启动: python backend/main.py")
    print("确保至少上传了一个文档")
    
    input("\n按Enter键开始测试...")
    
    # 测试用例
    test_cases = [
        {
            "name": "简单事实性问题",
            "query": "什么是人工智能？",
        },
        {
            "name": "复杂分析性问题",
            "query": "人工智能对教育行业的影响和挑战是什么？",
        },
        {
            "name": "观点性问题",
            "query": "如何看待人工智能的发展前景？",
        },
    ]
    
    # 测试1: Query Transformation RAG
    print_separator("1. Query Transformation RAG 测试")
    
    # 测试不同的转换策略
    strategies = ["rewrite", "stepback", "decompose", "hybrid"]
    
    for strategy in strategies:
        config = {
            "transformation_type": strategy,
            "num_subqueries": 3
        }
        test_query(
            "query_transformation_rag",
            test_cases[1]["query"],  # 使用复杂问题
            config
        )
        time.sleep(2)
    
    # 测试2: Adaptive RAG
    print_separator("2. Adaptive RAG 测试")
    print("\n测试不同类型的查询，观察自适应路由")
    
    for case in test_cases:
        print(f"\n--- {case['name']} ---")
        test_query(
            "adaptive_rag",
            case["query"]
        )
        time.sleep(2)
    
    # 测试3: Self RAG
    print_separator("3. Self RAG 测试")
    
    # 测试不同的支持分数阈值
    for min_score in [0, 1, 5]:
        config = {
            "min_support_score": min_score
        }
        print(f"\n--- 最低支持分数: {min_score} ---")
        test_query(
            "self_rag",
            test_cases[0]["query"],  # 使用事实性问题
            config
        )
        time.sleep(2)
    
    # 对比测试
    print_separator("4. 多技术对比测试")
    print("\n同时测试所有新技术")
    
    payload = {
        "query": test_cases[1]["query"],
        "rag_techniques": [
            "simple_rag",
            "query_transformation_rag",
            "adaptive_rag",
            "self_rag"
        ],
        "rag_config": {
            "transformation_type": "hybrid",
            "min_support_score": 1
        },
        "top_k": 3
    }
    
    print(f"查询: {payload['query']}")
    print(f"对比技术: {', '.join(payload['rag_techniques'])}")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/qa/query",
            json=payload,
            timeout=120
        )
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 对比完成! 总耗时: {elapsed_time:.2f}秒")
            
            # 显示对比结果
            if 'results' in result:
                print(f"\n{'技术':<30} {'文档数':<10} {'答案长度':<10}")
                print("-" * 50)
                for rag_result in result['results']:
                    tech_name = rag_result['rag_technique']
                    doc_count = len(rag_result['retrieved_docs'])
                    answer_len = len(rag_result['answer'])
                    print(f"{tech_name:<30} {doc_count:<10} {answer_len:<10}")
        else:
            print(f"\n❌ 失败! {response.text}")
            
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
    
    # 总结
    print_separator("测试完成")
    print("\n✅ 所有测试已完成！")
    print("\n📊 结果分析:")
    print("1. Query Transformation: 查看是否生成了转换后的查询")
    print("2. Adaptive RAG: 检查不同查询类型是否使用了不同策略")
    print("3. Self RAG: 观察检索决策和答案评估过程")
    print("\n💡 提示:")
    print("- 查看后端日志以了解详细处理过程")
    print("- 使用 Streamlit 前端进行可视化对比")
    print("- 调整配置参数以优化性能")


if __name__ == "__main__":
    main()

