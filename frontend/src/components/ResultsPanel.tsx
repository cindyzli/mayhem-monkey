import { AlertTriangle, AlertOctagon, AlertCircle, Info, ChevronDown, ChevronUp, CheckCircle } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useState } from 'react';
import type { Vulnerability, Severity } from './VulnerabilityScanner';
import defaultResultsPanelConfig from '../data/resultsPanelConfig.json';

interface ResultsPanelProps {
  vulnerabilities: Vulnerability[];
  config?: ResultsPanelConfig;
}

interface ResultsPanelConfig {
  headerTitle: string;
  headerSubtitle: {
    singular: string;
    plural: string;
  };
  detailSections: {
    description: string;
    codeSnippet: string;
    impact: string;
    recommendation: string;
  };
}

const severityConfig: Record<Severity, {
  icon: LucideIcon;
  color: string;
  bg: string;
  border: string;
  label: string;
}> = {
  critical: {
    icon: AlertOctagon,
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    label: 'Critical'
  },
  high: {
    icon: AlertTriangle,
    color: 'text-orange-400',
    bg: 'bg-orange-500/10',
    border: 'border-orange-500/30',
    label: 'High'
  },
  medium: {
    icon: AlertCircle,
    color: 'text-yellow-400',
    bg: 'bg-yellow-500/10',
    border: 'border-yellow-500/30',
    label: 'Medium'
  },
  low: {
    icon: Info,
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    label: 'Low'
  }
};

export function ResultsPanel({ vulnerabilities, config = defaultResultsPanelConfig }: ResultsPanelProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const mergedConfig = {
    headerTitle: config?.headerTitle ?? 'Scan Results',
    headerSubtitle: {
      singular: config?.headerSubtitle?.singular ?? 'Found {count} vulnerability',
      plural: config?.headerSubtitle?.plural ?? 'Found {count} vulnerabilities',
    },
    detailSections: {
      description: config?.detailSections?.description ?? 'Description',
      codeSnippet: config?.detailSections?.codeSnippet ?? 'Evidence',
      impact: config?.detailSections?.impact ?? 'Impact',
      recommendation: config?.detailSections?.recommendation ?? 'Recommendation',
    },
  };

  const toggleExpand = (id: string) => {
    const newExpanded = new Set(expandedIds);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedIds(newExpanded);
  };

  const criticalCount = vulnerabilities.filter(v => v.severity === 'critical').length;
  const highCount = vulnerabilities.filter(v => v.severity === 'high').length;
  const mediumCount = vulnerabilities.filter(v => v.severity === 'medium').length;
  const lowCount = vulnerabilities.filter(v => v.severity === 'low').length;
  const subtitleTemplate = vulnerabilities.length === 1
    ? mergedConfig.headerSubtitle.singular
    : mergedConfig.headerSubtitle.plural;
  const subtitle = subtitleTemplate.replace('{count}', String(vulnerabilities.length));

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-700 bg-gray-800/30">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium text-lg text-white">{mergedConfig.headerTitle}</h3>
            <p className="text-sm text-gray-400 mt-0.5">
              {subtitle}
            </p>
          </div>
          <CheckCircle className="w-6 h-6 text-green-400" />
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3 p-4 border-b border-gray-700">
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-red-400">{criticalCount}</div>
          <div className="text-xs text-gray-400 mt-1">{severityConfig.critical.label}</div>
        </div>
        <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-orange-400">{highCount}</div>
          <div className="text-xs text-gray-400 mt-1">{severityConfig.high.label}</div>
        </div>
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-yellow-400">{mediumCount}</div>
          <div className="text-xs text-gray-400 mt-1">{severityConfig.medium.label}</div>
        </div>
        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-blue-400">{lowCount}</div>
          <div className="text-xs text-gray-400 mt-1">{severityConfig.low.label}</div>
        </div>
      </div>

      <div className="divide-y divide-gray-700 max-h-[400px] overflow-y-auto">
        {vulnerabilities.map((vuln) => {
          const severity = severityConfig[vuln.severity] ?? severityConfig.medium;
          const Icon = severity.icon;
          const isExpanded = expandedIds.has(vuln.id);

          return (
            <div key={vuln.id} className="p-4 hover:bg-gray-700/30 transition-colors">
              <button
                onClick={() => toggleExpand(vuln.id)}
                className="w-full text-left"
              >
              <div className="flex flex-col">
                <div className="flex items-start gap-3">

                  <div className={`p-2 rounded-lg ${severity.bg} ${severity.border} border flex-shrink-0`}>
                    <Icon className={`w-5 h-5 ${severity.color}`} />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-100">{vuln.title}</h4>
                        <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${severity.bg} ${severity.color} border ${severity.border}`}>
                            {severity.label}
                          </span>
                          {vuln.line > 0 && (
                            <span className="text-xs text-gray-500">
                              Line {vuln.line}
                            </span>
                          )}
                          <span className="text-xs text-gray-500">
                            {vuln.category}
                          </span>
                        </div>
                      </div>
                        {isExpanded ? (
                          <ChevronUp className="w-5 h-5 text-gray-500 flex-shrink-0" />
                        ) : (
                          <ChevronDown className="w-5 h-5 text-gray-500 flex-shrink-0" />
                        )}
                      </div>
                    </div>
                  </div>

                  {!isExpanded && (
                    <p className="text-sm text-gray-400 flex-1 mt-2 line-clamp-2">
                      {vuln.description}
                    </p>
                  )}
                </div>
              </button>

              {isExpanded && (
                <div className="mt-4 space-y-4">
                  <div>
                    <h5 className="text-sm font-medium text-gray-300 mb-1.5">{mergedConfig.detailSections.description}</h5>
                    <p className="text-sm text-gray-400 leading-relaxed">{vuln.description}</p>
                  </div>

                  <div>
                    <h5 className="text-sm font-medium text-gray-300 mb-1.5">{mergedConfig.detailSections.codeSnippet}</h5>
                    <pre className="bg-gray-950 border border-gray-700 rounded-lg p-3 text-sm text-gray-300 overflow-x-auto">
                      <code>{vuln.codeSnippet}</code>
                    </pre>
                  </div>

                  <div>
                    <h5 className="text-sm font-medium text-gray-300 mb-1.5">{mergedConfig.detailSections.impact}</h5>
                    <p className="text-sm text-gray-400 leading-relaxed">{vuln.impact}</p>
                  </div>

                  <div>
                    <h5 className="text-sm font-medium text-gray-300 mb-1.5">{mergedConfig.detailSections.recommendation}</h5>
                    <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
                      <p className="text-sm text-gray-300 leading-relaxed">{vuln.recommendation}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
