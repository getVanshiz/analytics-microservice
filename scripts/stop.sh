
#!/bin/bash

echo "Stopping all kubectl port-forward processes..."

# Kill ANY kubectl port-forward processes (covers kubectl, kubectl1., etc.)
pkill -f "port-forward" 2>/dev/null || true

echo "All port-forwards stopped!"
