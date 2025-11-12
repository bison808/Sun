#!/bin/bash

# Schedule Daily Inference Pipeline
# Sets up automated daily predictions

set -e

echo "Setting up Daily Inference Pipeline Scheduler"
echo "=============================================="

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ML_DIR="$(dirname "$SCRIPT_DIR")"

# Activate virtual environment if it exists
if [ -d "$ML_DIR/venv" ]; then
    source "$ML_DIR/venv/bin/activate"
fi

# Choose scheduling method
echo ""
echo "Choose scheduling method:"
echo "1) Cron (traditional)"
echo "2) Systemd timer (modern Linux)"
echo "3) Manual setup (show commands only)"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo ""
        echo "Setting up Cron job..."

        # Cron job to run daily at 6:00 AM
        CRON_CMD="0 6 * * * cd $ML_DIR && $ML_DIR/venv/bin/python $SCRIPT_DIR/daily_inference.py >> $ML_DIR/logs/ml/daily_inference.log 2>&1"

        # Check if cron job already exists
        if crontab -l 2>/dev/null | grep -q "daily_inference.py"; then
            echo "Cron job already exists"
            read -p "Remove and recreate? [y/N]: " recreate
            if [[ $recreate == "y" || $recreate == "Y" ]]; then
                # Remove old cron job
                crontab -l 2>/dev/null | grep -v "daily_inference.py" | crontab -
                echo "Old cron job removed"
            else
                echo "Keeping existing cron job"
                exit 0
            fi
        fi

        # Add cron job
        (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

        echo "✓ Cron job added"
        echo ""
        echo "Schedule: Daily at 6:00 AM"
        echo "Log file: $ML_DIR/logs/ml/daily_inference.log"
        echo ""
        echo "To view current cron jobs: crontab -l"
        echo "To remove this job: crontab -e (then delete the line)"
        ;;

    2)
        echo ""
        echo "Setting up Systemd timer..."

        # Create systemd service file
        SERVICE_FILE="/tmp/solar-inference.service"
        cat > $SERVICE_FILE << EOF
[Unit]
Description=Solar Cycle Daily Inference Pipeline
After=network.target

[Service]
Type=oneshot
User=$USER
WorkingDirectory=$ML_DIR
ExecStart=$ML_DIR/venv/bin/python $SCRIPT_DIR/daily_inference.py
StandardOutput=append:$ML_DIR/logs/ml/daily_inference.log
StandardError=append:$ML_DIR/logs/ml/daily_inference.log

[Install]
WantedBy=multi-user.target
EOF

        # Create systemd timer file
        TIMER_FILE="/tmp/solar-inference.timer"
        cat > $TIMER_FILE << EOF
[Unit]
Description=Solar Cycle Daily Inference Timer
Requires=solar-inference.service

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 06:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

        echo "Created systemd files:"
        echo "  Service: $SERVICE_FILE"
        echo "  Timer: $TIMER_FILE"
        echo ""
        echo "To install, run these commands as root:"
        echo ""
        echo "  sudo cp $SERVICE_FILE /etc/systemd/system/"
        echo "  sudo cp $TIMER_FILE /etc/systemd/system/"
        echo "  sudo systemctl daemon-reload"
        echo "  sudo systemctl enable solar-inference.timer"
        echo "  sudo systemctl start solar-inference.timer"
        echo ""
        echo "To check status:"
        echo "  sudo systemctl status solar-inference.timer"
        echo "  sudo systemctl list-timers"
        echo ""
        echo "To run manually:"
        echo "  sudo systemctl start solar-inference.service"
        ;;

    3)
        echo ""
        echo "Manual Setup Commands"
        echo "===================="
        echo ""
        echo "1. Cron (runs daily at 6:00 AM):"
        echo "   crontab -e"
        echo "   # Add this line:"
        echo "   0 6 * * * cd $ML_DIR && $ML_DIR/venv/bin/python $SCRIPT_DIR/daily_inference.py >> $ML_DIR/logs/ml/daily_inference.log 2>&1"
        echo ""
        echo "2. Docker Compose (add to docker-compose.ml.yml):"
        echo "   services:"
        echo "     inference-cron:"
        echo "       image: solar-ml-api"
        echo "       command: bash -c \"while true; do python scripts/daily_inference.py; sleep 86400; done\""
        echo "       depends_on:"
        echo "         - ml-api"
        echo "         - redis"
        echo ""
        echo "3. Kubernetes CronJob:"
        echo "   apiVersion: batch/v1"
        echo "   kind: CronJob"
        echo "   metadata:"
        echo "     name: solar-inference"
        echo "   spec:"
        echo "     schedule: \"0 6 * * *\""
        echo "     jobTemplate:"
        echo "       spec:"
        echo "         template:"
        echo "           spec:"
        echo "             containers:"
        echo "             - name: inference"
        echo "               image: solar-ml-api:latest"
        echo "               command: [\"python\", \"scripts/daily_inference.py\"]"
        echo ""
        echo "4. Run manually now:"
        echo "   cd $ML_DIR"
        echo "   python scripts/daily_inference.py"
        ;;

    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✓ Daily inference pipeline scheduler setup complete!"
