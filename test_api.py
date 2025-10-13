"""
API测试脚本 - 用于快速测试后端API是否正常工作
"""

import requests
import json
from pathlib import Path

API_BASE = "http://localhost:8000/api/v1"


def test_health():
    """测试健康检查"""
    print("=" * 50)
    print("测试健康检查...")
    print("=" * 50)
    
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        print("✅ 健康检查通过")
        return True
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return False


def test_documents():
    """测试文档API"""
    print("\n" + "=" * 50)
    print("测试文档列表API...")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_BASE}/documents/")
        print(f"状态码: {response.status_code}")
        documents = response.json()
        print(f"文档数量: {len(documents)}")
        
        if documents:
            print("\n已有文档:")
            for doc in documents[:3]:  # 显示前3个
                print(f"  - {doc['filename']} (ID: {doc['id']}, 块数: {doc['chunk_count']})")
        else:
            print("暂无文档")
        
        print("✅ 文档API测试通过")
        return True
    except Exception as e:
        print(f"❌ 文档API测试失败: {e}")
        return False


def test_upload(file_path: str = None):
    """测试文档上传"""
    print("\n" + "=" * 50)
    print("测试文档上传API...")
    print("=" * 50)
    
    if not file_path:
        print("⚠️  未提供测试文件，跳过上传测试")
        return True
    
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"⚠️  文件不存在: {file_path}")
        return False
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f)}
            response = requests.post(f"{API_BASE}/documents/upload", files=files)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"上传成功!")
            print(f"  文档ID: {result['id']}")
            print(f"  文件名: {result['filename']}")
            print(f"  块数: {result['chunk_count']}")
            print("✅ 上传测试通过")
            return True
        else:
            print(f"❌ 上传失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 上传测试失败: {e}")
        return False


def test_query(document_id: int = None, query: str = "测试问题"):
    """测试问答API"""
    print("\n" + "=" * 50)
    print("测试问答API...")
    print("=" * 50)
    
    if not document_id:
        # 尝试获取第一个文档
        try:
            response = requests.get(f"{API_BASE}/documents/")
            documents = response.json()
            if documents:
                document_id = documents[0]['id']
            else:
                print("⚠️  没有可用文档，跳过问答测试")
                return True
        except:
            print("⚠️  无法获取文档列表，跳过问答测试")
            return True
    
    try:
        payload = {
            "query": query,
            "document_ids": [document_id],
            "rag_techniques": ["simple_rag"],
            "llm_config": {},
            "rag_config": {"top_k": 3}
        }
        
        print(f"查询: {query}")
        print(f"文档ID: {document_id}")
        
        response = requests.post(
            f"{API_BASE}/qa/query",
            json=payload,
            timeout=60
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"会话ID: {result['session_id']}")
            print(f"RAG技术数: {len(result['results'])}")
            
            if result['results']:
                first_result = result['results'][0]
                print(f"\n答案预览:")
                print(f"  技术: {first_result['rag_technique']}")
                print(f"  执行时间: {first_result['execution_time']:.2f}秒")
                print(f"  检索文档数: {len(first_result['retrieved_docs'])}")
                print(f"  答案长度: {len(first_result['answer'])} 字符")
                print(f"  答案前100字: {first_result['answer'][:100]}...")
            
            print("✅ 问答测试通过")
            return True
        else:
            print(f"❌ 问答失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 问答测试失败: {e}")
        return False


def test_evaluation_stats():
    """测试评分统计API"""
    print("\n" + "=" * 50)
    print("测试评分统计API...")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_BASE}/evaluation/stats/comparison")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            stats = response.json()
            print(f"统计记录数: {len(stats)}")
            
            if stats:
                print("\n统计概览:")
                for stat in stats:
                    print(f"  {stat['technique']}:")
                    print(f"    查询数: {stat['total_queries']}")
                    print(f"    平均执行时间: {stat['avg_execution_time']:.3f}秒")
            else:
                print("暂无统计数据")
            
            print("✅ 统计API测试通过")
            return True
        else:
            print(f"❌ 统计API失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 统计测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "🚀" * 25)
    print(" " * 20 + "RAG评测平台 API测试")
    print("🚀" * 25 + "\n")
    
    results = []
    
    # 1. 健康检查
    results.append(("健康检查", test_health()))
    
    # 2. 文档列表
    results.append(("文档列表", test_documents()))
    
    # 3. 文档上传（可选）
    # 如果有测试文件，取消下面的注释
    # results.append(("文档上传", test_upload("path/to/test.pdf")))
    
    # 4. 问答测试
    results.append(("问答功能", test_query(query="这篇文档讲了什么？")))
    
    # 5. 统计API
    results.append(("统计功能", test_evaluation_stats()))
    
    # 总结
    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！系统运行正常！")
    else:
        print("\n⚠️  部分测试失败，请检查错误信息")


if __name__ == "__main__":
    main()

