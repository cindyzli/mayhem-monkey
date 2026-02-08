import { Loader2, Mic, Search } from 'lucide-react';

interface ScanningProgressProps {
  progress: number;
  isListening?: boolean;
}

export function ScanningProgress({ progress, isListening }: ScanningProgressProps) {
  if (isListening) {
    return (
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
        <div className="flex items-center gap-3 mb-4">
          <Mic className="w-6 h-6 text-red-400 animate-pulse" />
          <div>
            <h3 className="font-medium text-lg text-white">Listening for Voice Command</h3>
            <p className="text-sm text-gray-400">Say "open example.com" or "scan example.com" to start</p>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-gray-800">
          <p className="text-xs text-gray-500">
            Supported phrases: "open [url]", "go to [url]", "attack [url]", "scan [url]", "test [url]"
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
      <div className="flex items-center gap-3 mb-4">
        <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
        <div>
          <h3 className="font-medium text-lg">Scanning for Vulnerabilities</h3>
          <p className="text-sm text-gray-400">Analyzing code and testing for security issues...</p>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex justify-between text-sm text-gray-400">
          <span>Progress</span>
          <span>{progress}%</span>
        </div>
        <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
          <div
            className="bg-blue-600 h-full transition-all duration-300 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-gray-800">
          <div className="flex items-center gap-2 text-sm">
            <Search className="w-4 h-4 text-gray-500" />
            <span className="text-gray-400">Testing injection attacks</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Search className="w-4 h-4 text-gray-500" />
            <span className="text-gray-400">Analyzing input validation</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Search className="w-4 h-4 text-gray-500" />
            <span className="text-gray-400">Checking authentication</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Search className="w-4 h-4 text-gray-500" />
            <span className="text-gray-400">Testing file operations</span>
          </div>
        </div>
      </div>
    </div>
  );
}
