const WebSocket = require('ws');
const logger = require('../utils/logger');
const noaaService = require('./noaaService');

class WebSocketService {
  constructor() {
    this.wss = null;
    this.clients = new Set();
    this.heartbeatInterval = null;
  }

  /**
   * Initialize WebSocket server
   */
  initialize(server) {
    this.wss = new WebSocket.Server({
      server,
      path: '/ws/live',
    });

    this.wss.on('connection', (ws, req) => {
      logger.info('WebSocket client connected', { ip: req.socket.remoteAddress });

      this.clients.add(ws);

      // Send initial data
      this.sendSolarUpdate(ws);

      // Handle messages from client
      ws.on('message', (message) => {
        try {
          const data = JSON.parse(message);
          this.handleClientMessage(ws, data);
        } catch (error) {
          logger.error('Invalid WebSocket message', { error: error.message });
        }
      });

      // Handle client disconnect
      ws.on('close', () => {
        this.clients.delete(ws);
        logger.info('WebSocket client disconnected');
      });

      // Handle errors
      ws.on('error', (error) => {
        logger.error('WebSocket error', { error: error.message });
        this.clients.delete(ws);
      });

      // Send ping to keep connection alive
      ws.isAlive = true;
      ws.on('pong', () => {
        ws.isAlive = true;
      });
    });

    // Start heartbeat
    this.startHeartbeat();

    // Start periodic updates
    this.startPeriodicUpdates();

    logger.info('WebSocket service initialized');
  }

  /**
   * Start heartbeat to detect dead connections
   */
  startHeartbeat() {
    const interval = parseInt(process.env.WS_HEARTBEAT_INTERVAL) || 30000;

    this.heartbeatInterval = setInterval(() => {
      this.wss.clients.forEach((ws) => {
        if (ws.isAlive === false) {
          this.clients.delete(ws);
          return ws.terminate();
        }

        ws.isAlive = false;
        ws.ping();
      });
    }, interval);
  }

  /**
   * Start periodic solar data updates
   */
  startPeriodicUpdates() {
    // Send updates every 5 minutes
    setInterval(async () => {
      await this.broadcastSolarUpdate();
    }, 5 * 60 * 1000);
  }

  /**
   * Handle messages from clients
   */
  handleClientMessage(ws, data) {
    switch (data.type) {
      case 'subscribe':
        logger.info('Client subscribed to updates');
        this.sendSolarUpdate(ws);
        break;
      case 'ping':
        ws.send(JSON.stringify({ type: 'pong', timestamp: new Date().toISOString() }));
        break;
      default:
        logger.warn('Unknown message type', { type: data.type });
    }
  }

  /**
   * Send solar update to a specific client
   */
  async sendSolarUpdate(ws) {
    try {
      const currentStatus = await noaaService.fetchCurrentStatus();

      const message = {
        type: 'solar_update',
        data: currentStatus,
        timestamp: new Date().toISOString(),
      };

      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
      }
    } catch (error) {
      logger.error('Failed to send solar update', { error: error.message });
    }
  }

  /**
   * Broadcast solar update to all connected clients
   */
  async broadcastSolarUpdate() {
    try {
      const currentStatus = await noaaService.fetchCurrentStatus();

      const message = {
        type: 'solar_update',
        data: currentStatus,
        timestamp: new Date().toISOString(),
      };

      this.broadcast(message);
      logger.info('Broadcasted solar update to clients', { clientCount: this.clients.size });
    } catch (error) {
      logger.error('Failed to broadcast solar update', { error: error.message });
    }
  }

  /**
   * Broadcast a message to all connected clients
   */
  broadcast(message) {
    const messageStr = JSON.stringify(message);

    this.clients.forEach((client) => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(messageStr);
      }
    });
  }

  /**
   * Stop the WebSocket service
   */
  stop() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }

    if (this.wss) {
      this.wss.close();
    }

    logger.info('WebSocket service stopped');
  }
}

module.exports = new WebSocketService();
