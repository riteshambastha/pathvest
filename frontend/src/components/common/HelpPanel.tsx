import React, { useEffect } from 'react';

export interface HelpSection {
  title: string;
  content: string;
  icon?: string;
}

export interface HelpContent {
  stepTitle: string;
  stepNumber: number;
  overview: string;
  sections: HelpSection[];
  technicalDetails?: {
    backend: string[];
    frontend: string[];
    dataFlow: string[];
  };
  tips?: string[];
}

interface HelpPanelProps {
  isOpen: boolean;
  onClose: () => void;
  content: HelpContent;
}

const HelpPanel: React.FC<HelpPanelProps> = ({ isOpen, onClose, content }) => {
  // Close on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Prevent body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black transition-opacity duration-300 z-40 ${
          isOpen ? 'opacity-50' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
      />

      {/* Sliding Panel */}
      <div
        className={`fixed top-0 right-0 h-full w-full md:w-2/3 lg:w-1/2 bg-white shadow-2xl transform transition-transform duration-300 ease-in-out z-50 ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="h-full flex flex-col">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-4 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-white bg-opacity-20 rounded-full p-2">
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h2 className="text-xl font-bold">
                  Step {content.stepNumber}: {content.stepTitle}
                </h2>
                <p className="text-blue-100 text-sm">Documentation & Help</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-white hover:bg-white hover:bg-opacity-20 rounded-full p-2 transition"
              aria-label="Close help panel"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
            {/* Overview */}
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-5 border border-blue-200">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 mt-1">
                  <svg className="h-6 w-6 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">Overview</h3>
                  <p className="text-gray-700 leading-relaxed">{content.overview}</p>
                </div>
              </div>
            </div>

            {/* Main Sections */}
            {content.sections.map((section, index) => (
              <div key={index} className="bg-white rounded-lg p-5 border border-gray-200 shadow-sm hover:shadow-md transition">
                <div className="flex items-start space-x-3">
                  {section.icon && (
                    <div className="flex-shrink-0 mt-1">
                      <span className="text-2xl">{section.icon}</span>
                    </div>
                  )}
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-3">{section.title}</h3>
                    <div 
                      className="text-gray-700 leading-relaxed prose prose-sm max-w-none"
                      dangerouslySetInnerHTML={{ __html: section.content }}
                    />
                  </div>
                </div>
              </div>
            ))}

            {/* Technical Details */}
            {content.technicalDetails && (
              <div className="bg-gray-50 rounded-lg p-5 border border-gray-300">
                <div className="flex items-start space-x-3 mb-4">
                  <svg className="h-6 w-6 text-gray-600 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                  </svg>
                  <h3 className="text-lg font-semibold text-gray-900">Technical Details</h3>
                </div>
                
                <div className="space-y-4">
                  {content.technicalDetails.backend.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center">
                        <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs mr-2">Backend</span>
                        What Runs in the Background
                      </h4>
                      <ul className="space-y-1 text-sm text-gray-600">
                        {content.technicalDetails.backend.map((item, i) => (
                          <li key={i} className="flex items-start">
                            <span className="text-green-600 mr-2">▸</span>
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {content.technicalDetails.frontend.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center">
                        <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs mr-2">Frontend</span>
                        What You See
                      </h4>
                      <ul className="space-y-1 text-sm text-gray-600">
                        {content.technicalDetails.frontend.map((item, i) => (
                          <li key={i} className="flex items-start">
                            <span className="text-blue-600 mr-2">▸</span>
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {content.technicalDetails.dataFlow.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center">
                        <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded text-xs mr-2">Data Flow</span>
                        How It Works
                      </h4>
                      <ul className="space-y-1 text-sm text-gray-600">
                        {content.technicalDetails.dataFlow.map((item, i) => (
                          <li key={i} className="flex items-start">
                            <span className="text-purple-600 mr-2">→</span>
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Tips */}
            {content.tips && content.tips.length > 0 && (
              <div className="bg-gradient-to-br from-amber-50 to-yellow-50 rounded-lg p-5 border border-amber-200">
                <div className="flex items-start space-x-3">
                  <svg className="h-6 w-6 text-amber-600 mt-1 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-3">💡 Pro Tips</h3>
                    <ul className="space-y-2">
                      {content.tips.map((tip, i) => (
                        <li key={i} className="text-gray-700 text-sm flex items-start">
                          <span className="text-amber-600 mr-2 font-bold">{i + 1}.</span>
                          <span>{tip}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-gray-200 px-6 py-4 bg-gray-50">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                Press <kbd className="px-2 py-1 bg-white border border-gray-300 rounded text-xs font-mono">ESC</kbd> to close
              </div>
              <button
                onClick={onClose}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium"
              >
                Got it!
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default HelpPanel;

