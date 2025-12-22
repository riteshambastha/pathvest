import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

interface BacktestProgressModalProps {
  backtestId: string;
  onComplete: () => void;
  onClose: () => void;
}

interface ProgressUpdate {
  status: string;
  progress?: number;
  message?: string;
  current_step?: string;
  eta_seconds?: number;
  timestamp?: string;
}

const BacktestProgressModal: React.FC<BacktestProgressModalProps> = ({ backtestId, onComplete, onClose }) => {
  const navigate = useNavigate();
  const [progress, setProgress] = useState<ProgressUpdate>({ status: 'queued', progress: 0 });
  const [logs, setLogs] = useState<string[]>([]);
  const [isCompleted, setIsCompleted] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  useEffect(() => {
    const pollProgress = async () => {
      try {
        const response = await fetch(
          `${import.meta.env.VITE_API_BASE_URL}/api/v1/backtest/${backtestId}/status`
        );
        const data = await response.json();

        setProgress(data);

        // Add new log message
        if (data.message && !logs.includes(data.message)) {
          setLogs((prev) => [
            ...prev,
            `[${new Date().toLocaleTimeString()}] ${data.current_step || data.status}: ${data.message}`,
          ]);
        }

        // Check if completed or failed
        if (data.status === 'completed' || data.status === 'failed') {
          setIsCompleted(true);
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
          }
        }
      } catch (error) {
        console.error('Error polling progress:', error);
        setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] Error: ${error}`]);
      }
    };

    // Initial poll
    pollProgress();

    // Set up polling every 2 seconds
    pollIntervalRef.current = setInterval(pollProgress, 2000);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [backtestId, logs]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'failed':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'running':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <svg className="w-6 h-6 text-green-600" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
        );
      case 'failed':
        return (
          <svg className="w-6 h-6 text-red-600" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
        );
      case 'running':
        return (
          <svg className="w-6 h-6 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        );
      default:
        return (
          <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
    }
  };

  const formatTime = (seconds?: number) => {
    if (!seconds) return 'Calculating...';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  const handleViewResults = () => {
    navigate(`/results/${backtestId}`);
  };

  const handleGoToStrategies = () => {
    onComplete();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-5 text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {getStatusIcon(progress.status)}
              <div>
                <h2 className="text-xl font-bold">
                  {progress.status === 'completed'
                    ? 'Backtest Complete!'
                    : progress.status === 'failed'
                    ? 'Backtest Failed'
                    : 'Running Backtest...'}
                </h2>
                <p className="text-blue-100 text-sm">ID: {backtestId}</p>
              </div>
            </div>
            {!isCompleted && (
              <button
                onClick={onClose}
                className="text-white hover:bg-white/20 rounded-lg p-2 transition"
                title="Close (backtest will continue in background)"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              {progress.current_step || progress.status}
            </span>
            <span className="text-sm font-medium text-gray-900">
              {Math.round(progress.progress || 0)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                progress.status === 'completed'
                  ? 'bg-green-500'
                  : progress.status === 'failed'
                  ? 'bg-red-500'
                  : 'bg-blue-500 animate-pulse'
              }`}
              style={{ width: `${progress.progress || 0}%` }}
            />
          </div>
          {progress.eta_seconds !== undefined && progress.eta_seconds > 0 && (
            <p className="text-xs text-gray-600 mt-2">
              Estimated time remaining: {formatTime(progress.eta_seconds)}
            </p>
          )}
        </div>

        {/* Logs Console */}
        <div className="flex-1 overflow-hidden flex flex-col">
          <div className="px-6 py-3 bg-gray-800 border-b border-gray-700 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                <div className="w-3 h-3 rounded-full bg-green-500" />
              </div>
              <span className="text-xs font-mono text-gray-400 ml-2">Console Output</span>
            </div>
            <button
              onClick={() => setLogs([])}
              className="text-xs text-gray-400 hover:text-white transition"
            >
              Clear
            </button>
          </div>
          <div className="flex-1 overflow-y-auto bg-gray-900 px-6 py-4 font-mono text-sm">
            {logs.length === 0 ? (
              <p className="text-gray-500">Waiting for backtest to start...</p>
            ) : (
              logs.map((log, index) => (
                <div key={index} className="text-green-400 mb-1 leading-relaxed">
                  {log}
                </div>
              ))
            )}
            <div ref={logsEndRef} />
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
            {isCompleted ? (
              <span>Backtest {progress.status}</span>
            ) : (
              <span>You can close this window. Backtest will continue in the background.</span>
            )}
          </div>
          <div className="flex gap-3">
            {isCompleted && progress.status === 'completed' && (
              <>
                <button
                  onClick={handleGoToStrategies}
                  className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition font-medium"
                >
                  Go to My Strategies
                </button>
                <button
                  onClick={handleViewResults}
                  className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 transition font-medium flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  View Results
                </button>
              </>
            )}
            {isCompleted && progress.status === 'failed' && (
              <button
                onClick={onClose}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition font-medium"
              >
                Close
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BacktestProgressModal;

