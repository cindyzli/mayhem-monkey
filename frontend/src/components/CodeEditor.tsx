import { FileCode2 } from 'lucide-react';

interface CodeEditorProps {
  code: string;
  onChange: (code: string) => void;
}

export function CodeEditor({ code, onChange }: CodeEditorProps) {
  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-800 bg-gray-900/50">
        <FileCode2 className="w-5 h-5 text-blue-400" />
        <span className="font-medium">Code Editor</span>
        <span className="text-sm text-gray-500 ml-auto">
          {code.split('\n').length} lines
        </span>
      </div>
      <div className="relative">
        <textarea
          value={code}
          onChange={(e) => onChange(e.target.value)}
          className="w-full h-[500px] p-4 bg-gray-950 text-gray-100 font-mono text-sm resize-none focus:outline-none"
          spellCheck={false}
          placeholder="Paste your code here for vulnerability analysis..."
        />
        <div className="absolute top-0 left-0 w-12 h-full bg-gray-900/50 border-r border-gray-800 pointer-events-none">
          <div className="p-4 font-mono text-sm text-gray-600 text-right">
            {Array.from({ length: code.split('\n').length }, (_, i) => (
              <div key={i}>{i + 1}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
