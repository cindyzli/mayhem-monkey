import { Play, Settings } from 'lucide-react';

interface TestPanelProps {
  selectedTests: string[];
  onTestsChange: (tests: string[]) => void;
  onStartScan: () => void;
  isScanning: boolean;
}

const testCategories = [
  { id: 'sql-injection', name: 'SQL Injection', description: 'Detects SQL injection vulnerabilities' },
  { id: 'xss', name: 'Cross-Site Scripting', description: 'Identifies XSS attack vectors' },
  { id: 'csrf', name: 'CSRF Protection', description: 'Checks for CSRF vulnerabilities' },
  { id: 'authentication', name: 'Authentication', description: 'Tests auth implementation' },
  { id: 'authorization', name: 'Authorization', description: 'Validates access controls' },
  { id: 'encryption', name: 'Encryption', description: 'Checks data encryption' },
  { id: 'input-validation', name: 'Input Validation', description: 'Tests input sanitization' },
  { id: 'file-upload', name: 'File Upload', description: 'Validates file upload security' },
  { id: 'session-management', name: 'Session Management', description: 'Tests session security' },
  { id: 'api-security', name: 'API Security', description: 'Checks API vulnerabilities' },
];

export function TestPanel({ selectedTests, onTestsChange, onStartScan, isScanning }: TestPanelProps) {
  const toggleTest = (testId: string) => {
    if (selectedTests.includes(testId)) {
      onTestsChange(selectedTests.filter(id => id !== testId));
    } else {
      onTestsChange([...selectedTests, testId]);
    }
  };

  const selectAll = () => {
    onTestsChange(testCategories.map(t => t.id));
  };

  const deselectAll = () => {
    onTestsChange([]);
  };

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-700">
        <Settings className="w-5 h-5 text-blue-400" />
        <span className="font-medium text-white">Test Configuration</span>
      </div>

      <div className="p-4 space-y-4">
        <button
          onClick={onStartScan}
          disabled={isScanning || selectedTests.length === 0}
          className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white px-4 py-3 rounded-lg font-medium transition-colors shadow-lg"
        >
          <Play className="w-5 h-5" />
          {isScanning ? 'Scanning in Progress...' : 'Start Vulnerability Scan'}
        </button>

        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">
            {selectedTests.length} of {testCategories.length} tests selected
          </span>
          <div className="flex gap-2">
            <button
              onClick={selectAll}
              className="text-blue-400 hover:text-blue-300 transition-colors"
            >
              All
            </button>
            <span className="text-gray-600">|</span>
            <button
              onClick={deselectAll}
              className="text-blue-400 hover:text-blue-300 transition-colors"
            >
              None
            </button>
          </div>
        </div>

        <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2">
          {testCategories.map(test => (
            <label
              key={test.id}
              className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-700/50 cursor-pointer transition-colors border border-transparent hover:border-gray-600"
            >
              <div className="relative flex items-center justify-center w-5 h-5 mt-0.5">
                <input
                  type="checkbox"
                  checked={selectedTests.includes(test.id)}
                  onChange={() => toggleTest(test.id)}
                  className="w-5 h-5 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 cursor-pointer"
                />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm text-gray-200">{test.name}</div>
                <div className="text-xs text-gray-500 mt-0.5">{test.description}</div>
              </div>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
