#!/bin/bash

# RAG评测平台 - 一键启动脚本

echo "============================================"
echo "一键启动RAG评测平台"
echo "============================================"

# 检查tmux
if ! command -v tmux &> /dev/null; then
    echo "警告: 未安装tmux，将使用后台进程启动"
    
    # 启动后端
    echo "启动后端服务..."
    bash start_backend.sh &
    BACKEND_PID=$!
    
    # 等待后端启动
    echo "等待后端服务启动..."
    sleep 5
    
    # 启动前端
    echo "启动前端界面..."
    bash start_frontend.sh &
    FRONTEND_PID=$!
    
    echo ""
    echo "============================================"
    echo "服务启动完成！"
    echo "后端PID: $BACKEND_PID"
    echo "前端PID: $FRONTEND_PID"
    echo "============================================"
    echo "后端API: http://localhost:8000/docs"
    echo "前端界面: http://localhost:8501"
    echo "============================================"
    echo "停止服务: kill $BACKEND_PID $FRONTEND_PID"
    echo ""
    
    wait
else
    # 使用tmux启动
    SESSION="rag_eval"
    
    # 创建新会话并分离
    tmux new-session -d -s $SESSION
    
    # 分割窗口
    tmux split-window -h -t $SESSION
    
    # 左侧窗口启动后端
    tmux send-keys -t $SESSION:0.0 "bash start_backend.sh" C-m
    
    # 右侧窗口启动前端
    tmux send-keys -t $SESSION:0.1 "sleep 5 && bash start_frontend.sh" C-m
    
    echo ""
    echo "============================================"
    echo "服务已在tmux会话中启动！"
    echo "============================================"
    echo "后端API: http://localhost:8000/docs"
    echo "前端界面: http://localhost:8501"
    echo "============================================"
    echo "进入会话: tmux attach -t $SESSION"
    echo "退出会话: Ctrl+B, D"
    echo "停止服务: tmux kill-session -t $SESSION"
    echo ""
fi

