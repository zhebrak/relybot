# Remove previous data
rm -f *.log
rm -f *.storage
rm -f *.state_machine

# Start
python bot.py --node "8000" --cluster "8000 8001 8002" &
python bot.py --node "8001" --cluster "8000 8001 8002" &
python bot.py --node "8002" --cluster "8000 8001 8002" &
