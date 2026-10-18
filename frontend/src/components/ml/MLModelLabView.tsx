import React, { useState, useEffect } from 'react';
import {
  AlertCircle,
  BarChart2,
  CheckCircle2,
  Cpu,
  Play,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { api } from '../../services/api';
import type { MLMetricsResponse, MLPredictResponse } from '../../types/api';

export const MLModelLabView: React.FC = () => {
  const [metrics, setMetrics] = useState<MLMetricsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Prediction Playground State
  const [inputText, setInputText] = useState<string>('Deep pothole near flyover causing vehicle damage and traffic jam');
  const [predicting, setPredicting] = useState<boolean>(false);
  const [predictResult, setPredictResult] = useState<MLPredictResponse | null>(null);
  const [predictError, setPredictError] = useState<string | null>(null);

  const [activePartition, setActivePartition] = useState<'test' | 'challenge'>('test');

  const loadMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMLMetrics();
      setMetrics(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch ML metrics from backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, []);

  const handlePredict = async (sampleText?: string) => {
    const textToSubmit = sampleText || inputText;
    if (!textToSubmit.trim()) return;
    if (sampleText) setInputText(sampleText);

    setPredicting(true);
    setPredictError(null);
    try {
      const res = await api.predictComplaint(textToSubmit);
      setPredictResult(res);
    } catch (err: any) {
      setPredictError(err.message || 'Prediction request failed.');
    } finally {
      setPredicting(false);
    }
  };

  const sampleComplaints = [
    { text: 'Severe deep pothole on Ring Road near Mayur Vihar flyover.', label: 'Pothole' },
    { text: 'Heavy rainfall caused acute waterlogging with water knee-deep.', label: 'Waterlogging' },
    { text: 'Massive garbage pile overflowing on the pavement attracting stray animals.', label: 'Garbage' },
    { text: 'Sadak par bahut bada gaddha hai, accident ho sakta hai.', label: 'Pothole (Hinglish)' },
  ];

  const evalReport = metrics?.evaluation_report;
  const currentMetrics = activePartition === 'test'
    ? evalReport?.test_partition_metrics
    : evalReport?.challenge_set_metrics;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E2E8F0] pb-5">
        <div>
          <h2 className="text-2xl font-bold text-[#172033] tracking-tight flex items-center gap-2">
            <Cpu className="w-6 h-6 text-teal-700" />
            Machine Learning Intelligence Lab
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Production NLP classifier evaluation metrics, per-class performance, confusion matrices, and live inference engine.
          </p>
        </div>

        <button
          onClick={loadMetrics}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-semibold rounded-lg border border-[#E2E8F0] bg-white hover:bg-slate-50 text-slate-700 shadow-xs transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-teal-600' : 'text-slate-500'}`} />
          Refresh Model Status
        </button>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl border border-rose-200 bg-rose-50 text-rose-800 text-xs flex items-center gap-2 shadow-xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Model Overview & Vision Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl border border-[#E2E8F0] bg-white shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase text-slate-500 font-semibold">NLP Classifier</span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
              metrics?.is_available ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-rose-50 text-rose-800 border border-rose-200'
            }`}>
              {metrics?.is_available ? 'READY / ONLINE' : 'UNAVAILABLE'}
            </span>
          </div>
          <div className="text-lg font-bold text-[#172033] tracking-tight">
            {metrics?.model_name || 'TFIDF-LogisticRegression'}
          </div>
          <p className="text-[11px] text-slate-500 font-mono">
            Version: {metrics?.model_version || 'v1.0.0'} • Classes: {metrics?.classes?.join(', ') || 'pothole, waterlogging, garbage'}
          </p>
        </div>

        <div className="p-4 rounded-xl border border-[#E2E8F0] bg-white shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase text-slate-500 font-semibold">Vision Provider</span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
              metrics?.vision_provider?.is_configured ? 'bg-teal-50 text-teal-800 border border-teal-200' : 'bg-amber-50 text-amber-800 border border-amber-200'
            }`}>
              {metrics?.vision_provider?.is_configured ? 'CONFIGURED' : 'OPTIONAL / OFFLINE'}
            </span>
          </div>
          <div className="text-lg font-bold text-[#172033] tracking-tight">
            {metrics?.vision_provider?.name || 'Groq Vision LLM'}
          </div>
          <p className="text-[11px] text-slate-500">
            {metrics?.vision_provider?.is_configured ? 'Live API key detected. Full multimodal vision inference enabled.' : 'Operating in fallback mode (safe degraded intake active).'}
          </p>
        </div>

        <div className="p-4 rounded-xl border border-[#E2E8F0] bg-white shadow-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase text-slate-500 font-semibold">Model Artifact</span>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono text-slate-600 bg-slate-100 border border-slate-200 font-medium">
              Joblib Binary
            </span>
          </div>
          <div className="text-xs font-mono text-slate-700 truncate" title={metrics?.artifact_path}>
            {metrics?.artifact_path || 'artifacts/nlp_classifier.joblib'}
          </div>
          <p className="text-[11px] text-slate-500">
            Calibrated probabilistic pipeline: TF-IDF Char/Word N-grams + Multinomial Logistic Regression.
          </p>
        </div>
      </div>

      {/* Model Performance Evaluation Dashboard */}
      <div className="p-5 rounded-2xl border border-[#E2E8F0] bg-white shadow-xs space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E2E8F0] pb-3">
          <div>
            <h3 className="text-base font-bold text-[#172033] flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-teal-700" />
              Empirical Evaluation Metrics
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Metrics calculated directly from evaluated test partitions in <code className="font-mono text-teal-800 bg-slate-100 px-1 py-0.5 rounded text-[11px]">eval/nlp_metrics.json</code>.
            </p>
          </div>

          <div className="flex items-center gap-1.5 p-1 rounded-lg border border-[#E2E8F0] bg-slate-50 text-xs">
            <button
              onClick={() => setActivePartition('test')}
              className={`px-3 py-1 rounded font-medium transition-colors ${
                activePartition === 'test' ? 'bg-teal-700 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Test Split (60 samples)
            </button>
            <button
              onClick={() => setActivePartition('challenge')}
              className={`px-3 py-1 rounded font-medium transition-colors ${
                activePartition === 'challenge' ? 'bg-teal-700 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Challenge Set (30 samples)
            </button>
          </div>
        </div>

        {currentMetrics ? (
          <div className="space-y-6">
            {/* Top Score Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl border border-[#E2E8F0] bg-slate-50/70">
                <span className="text-[10px] font-mono text-slate-500 uppercase font-semibold">Accuracy</span>
                <div className="text-2xl font-black font-mono text-teal-800 mt-1">
                  {(currentMetrics.accuracy * 100).toFixed(1)}%
                </div>
              </div>
              <div className="p-4 rounded-xl border border-[#E2E8F0] bg-slate-50/70">
                <span className="text-[10px] font-mono text-slate-500 uppercase font-semibold">Macro F1 Score</span>
                <div className="text-2xl font-black font-mono text-emerald-700 mt-1">
                  {(currentMetrics.macro_f1 * 100).toFixed(1)}%
                </div>
              </div>
              <div className="p-4 rounded-xl border border-[#E2E8F0] bg-slate-50/70">
                <span className="text-[10px] font-mono text-slate-500 uppercase font-semibold">Macro Precision</span>
                <div className="text-2xl font-black font-mono text-blue-700 mt-1">
                  {(currentMetrics.macro_precision * 100).toFixed(1)}%
                </div>
              </div>
              <div className="p-4 rounded-xl border border-[#E2E8F0] bg-slate-50/70">
                <span className="text-[10px] font-mono text-slate-500 uppercase font-semibold">Macro Recall</span>
                <div className="text-2xl font-black font-mono text-amber-700 mt-1">
                  {(currentMetrics.macro_recall * 100).toFixed(1)}%
                </div>
              </div>
            </div>

            {/* Per-Class Table & Confusion Matrix Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Per-Class Performance Table */}
              <div className="space-y-3">
                <h4 className="text-xs font-mono font-bold uppercase text-slate-700">
                  Per-Class Classification Performance
                </h4>
                <div className="rounded-xl border border-[#E2E8F0] overflow-hidden bg-white">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-slate-50 text-slate-600 border-b border-[#E2E8F0] text-[10px] uppercase font-mono">
                      <tr>
                        <th className="py-2.5 px-3">Class</th>
                        <th className="py-2.5 px-3">Precision</th>
                        <th className="py-2.5 px-3">Recall</th>
                        <th className="py-2.5 px-3">F1-Score</th>
                        <th className="py-2.5 px-3 text-right">Support</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E2E8F0] font-mono">
                      {Object.entries(currentMetrics.per_class).map(([className, score]: [string, any]) => (
                        <tr key={className} className="hover:bg-slate-50/60 transition-colors">
                          <td className="py-2.5 px-3 capitalize font-bold text-slate-800">
                            {className}
                          </td>
                          <td className="py-2.5 px-3 text-teal-800 font-semibold">
                            {(score.precision * 100).toFixed(1)}%
                          </td>
                          <td className="py-2.5 px-3 text-blue-800 font-semibold">
                            {(score.recall * 100).toFixed(1)}%
                          </td>
                          <td className="py-2.5 px-3 text-emerald-800 font-bold">
                            {(score.f1 * 100).toFixed(1)}%
                          </td>
                          <td className="py-2.5 px-3 text-right text-slate-500 font-medium">
                            {score.support}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Confusion Matrix Visualization */}
              <div className="space-y-3">
                <h4 className="text-xs font-mono font-bold uppercase text-slate-700">
                  Confusion Matrix (Predicted vs Actual)
                </h4>
                <div className="p-4 rounded-xl border border-[#E2E8F0] bg-slate-50/50 flex flex-col items-center justify-center">
                  <div className="w-full max-w-sm">
                    <div className="text-[10px] text-center font-mono text-slate-500 uppercase tracking-wider mb-2 font-medium">
                      Predicted Class →
                    </div>
                    <div className="grid grid-cols-4 gap-1.5 text-center text-xs font-mono">
                      <div className="text-[10px] text-slate-400 flex items-center justify-end pr-2 font-medium">Actual ↓</div>
                      {currentMetrics.confusion_matrix.classes.map((c) => (
                        <div key={c} className="text-[10px] font-bold text-slate-600 capitalize truncate p-1">
                          {c.slice(0, 5)}
                        </div>
                      ))}

                      {currentMetrics.confusion_matrix.matrix.map((row, rIdx) => (
                        <React.Fragment key={rIdx}>
                          <div className="text-[10px] font-bold text-slate-600 capitalize flex items-center justify-end pr-2 truncate">
                            {currentMetrics.confusion_matrix.classes[rIdx].slice(0, 5)}
                          </div>
                          {row.map((val, cIdx) => {
                            const isDiagonal = rIdx === cIdx;
                            return (
                              <div
                                key={cIdx}
                                className={`p-3 rounded-lg border font-bold transition-all ${
                                  isDiagonal
                                    ? 'bg-teal-50 border-teal-300 text-teal-800 shadow-xs'
                                    : val > 0
                                    ? 'bg-rose-50 border-rose-300 text-rose-800'
                                    : 'bg-white border-[#E2E8F0] text-slate-400 font-normal'
                                }`}
                              >
                                {val}
                              </div>
                            );
                          })}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-8 text-center text-slate-500 text-xs">
            Evaluation metrics not found. Run <code className="text-teal-700 font-mono font-semibold">python -m app.ml.nlp_classifier --train</code> to generate evaluation report.
          </div>
        )}
      </div>

      {/* Live Inference Prediction Playground */}
      <div className="p-5 rounded-2xl border border-[#E2E8F0] bg-white shadow-xs space-y-4">
        <div>
          <h3 className="text-base font-bold text-[#172033] flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-teal-700" />
            Live NLP Inference Playground
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Submit sample civic complaint texts directly to the active model for live probabilistic categorization.
          </p>
        </div>

        {/* Quick Sample Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-mono text-slate-500 font-semibold">Sample Inputs:</span>
          {sampleComplaints.map((item, idx) => (
            <button
              key={idx}
              onClick={() => handlePredict(item.text)}
              className="px-2.5 py-1 text-[11px] rounded-lg border border-[#E2E8F0] bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium transition-colors"
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Input Textarea & Submit */}
        <div className="space-y-2">
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            rows={3}
            placeholder="Type or paste a complaint description in English or Hinglish..."
            className="w-full p-3 rounded-xl border border-[#E2E8F0] bg-slate-50/50 text-[#172033] placeholder-slate-400 text-xs font-sans focus:outline-none focus:bg-white focus:border-teal-600 focus:ring-1 focus:ring-teal-600 transition-all"
          />

          <div className="flex items-center justify-between">
            <span className="text-[11px] text-slate-400 font-mono">
              {inputText.length} / 2000 characters
            </span>
            <button
              onClick={() => handlePredict()}
              disabled={predicting || !inputText.trim()}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg font-bold text-xs bg-teal-700 hover:bg-teal-800 text-white shadow-xs transition-all disabled:opacity-50"
            >
              <Play className={`w-3.5 h-3.5 fill-current ${predicting ? 'animate-spin' : ''}`} />
              {predicting ? 'Classifying...' : 'Predict Category'}
            </button>
          </div>
        </div>

        {predictError && (
          <div className="p-3 rounded-lg border border-rose-200 bg-rose-50 text-rose-800 text-xs flex items-center gap-2 shadow-xs">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{predictError}</span>
          </div>
        )}

        {/* Prediction Results Card */}
        {predictResult && (
          <div className="p-4 rounded-xl border border-teal-200 bg-teal-50/30 space-y-3 animate-in fade-in duration-200">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-teal-200/60 pb-2">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0" />
                <span className="text-xs font-mono text-slate-500 font-medium">Predicted Classification:</span>
                <span className="text-sm font-bold uppercase text-teal-900 font-mono">
                  {predictResult.predicted_label || 'UNCERTAIN'}
                </span>
              </div>
              <div className="text-xs font-mono text-slate-600">
                Confidence: <strong className="text-teal-800 font-bold">{((predictResult.confidence || 0) * 100).toFixed(1)}%</strong>
              </div>
            </div>

            {/* Score Breakdown Bars */}
            <div className="space-y-2">
              <span className="text-[11px] font-mono uppercase text-slate-500 font-semibold">Class Probabilities:</span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {Object.entries(predictResult.scores).map(([cls, prob]) => (
                  <div key={cls} className="p-3 rounded-lg border border-[#E2E8F0] bg-white space-y-1.5 shadow-xs">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="capitalize text-slate-700 font-medium">{cls}</span>
                      <span className="font-bold text-teal-800">{(prob * 100).toFixed(1)}%</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                      <div
                        className="h-full bg-teal-600 rounded-full transition-all duration-500"
                        style={{ width: `${prob * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
