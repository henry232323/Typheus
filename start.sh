running=1

finish()
{
    running=0
}

trap finish SIGINT

while (( running )); do
    python3 Typheus.py
    echo "Restarting server on crash.."
    sleep 5
done