import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'

export default function App() {
  const [complaint, setComplaint] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)

  const handleSubmit = async () => {
    setLoading(true)
    setResult(null)
    try {
      const res = await fetch('http://localhost:8000/api/incidents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ complaint })
      })
      const data = await res.json()
      setResult(data)
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 p-8 font-sans">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header */}
        <header className="flex items-center justify-between border-b border-slate-800 pb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-teal-400">JANSETU AI</h1>
            <p className="text-slate-400 mt-1">Adaptive Civic Incident Resolution Command Center</p>
          </div>
          <div className="flex gap-4">
            <Badge variant="outline" className="border-teal-500/30 text-teal-300 bg-teal-500/10">System Online</Badge>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Column: Input */}
          <div className="lg:col-span-1 space-y-6">
            <Card className="bg-slate-900 border-slate-800 shadow-xl shadow-slate-900/50">
              <CardHeader>
                <CardTitle className="text-slate-200">New Incident Report</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea 
                  placeholder="Describe the civic incident (e.g., 'Huge pothole on Main St...')"
                  className="bg-slate-950 border-slate-800 text-slate-200 focus-visible:ring-teal-500 min-h-[120px]"
                  value={complaint}
                  onChange={e => setComplaint(e.target.value)}
                />
                <Button 
                  onClick={handleSubmit} 
                  disabled={loading || !complaint}
                  className="w-full bg-teal-600 hover:bg-teal-500 text-white font-medium"
                >
                  {loading ? 'Processing through Agents...' : 'Dispatch Agents'}
                </Button>
              </CardContent>
            </Card>

            {/* If we have an audit timeline, we can render it here or right */}
          </div>

          {/* Right Column: Results & Timeline */}
          <div className="lg:col-span-2 space-y-6">
            {result ? (
              <div className="space-y-6">
                
                {/* Status & Priority */}
                <div className="grid grid-cols-2 gap-4">
                  <Card className="bg-slate-900 border-slate-800">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-slate-400">Final Status</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold text-teal-400">{result.status}</div>
                    </CardContent>
                  </Card>

                  <Card className="bg-slate-900 border-slate-800">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-slate-400">Priority Score</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold text-amber-400">
                        {result.priority?.priority_score || 'N/A'} / 100
                      </div>
                      <p className="text-xs text-slate-500 mt-1">{result.priority?.priority_band}</p>
                    </CardContent>
                  </Card>
                </div>

                {/* Extracted Facts */}
                {result.extracted_facts && (
                  <Card className="bg-slate-900 border-slate-800">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-slate-400">Incident Intelligence</CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-slate-300">
                      <p><span className="text-slate-500">Category:</span> {result.extracted_facts.category}</p>
                      <p className="mt-1"><span className="text-slate-500">Severity Indicators:</span> {result.extracted_facts.severity_indicators.join(', ')}</p>
                    </CardContent>
                  </Card>
                )}

                {/* Plan */}
                {result.current_plan && (
                  <Card className="bg-slate-900 border-slate-800">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-slate-400">Resolution Plan</CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-slate-300 space-y-2">
                      <div>
                        <span className="text-slate-500 block">Mitigation Steps:</span>
                        <ul className="list-disc pl-5 mt-1 space-y-1 text-slate-300">
                          {result.current_plan.mitigation_steps.map((step: string, i: number) => <li key={i}>{step}</li>)}
                        </ul>
                      </div>
                      <div className="mt-4">
                        <span className="text-slate-500 block">Required Resources:</span>
                        <div className="flex gap-2 flex-wrap mt-2">
                          {result.current_plan.required_resources.map((res: string, i: number) => (
                            <Badge key={i} variant="secondary" className="bg-slate-800 text-slate-300 border-slate-700">{res}</Badge>
                          ))}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Timeline */}
                <Card className="bg-slate-900 border-slate-800">
                  <CardHeader>
                    <CardTitle className="text-sm font-medium text-slate-400">Agent Audit Trace</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {result.audit_timeline?.map((event: any, i: number) => (
                        <div key={i} className="flex gap-4 items-start border-l-2 border-slate-800 pl-4 py-1 relative">
                          <div className="absolute w-2.5 h-2.5 bg-teal-500 rounded-full -left-[6px] top-2" />
                          <div>
                            <div className="text-xs text-teal-400 font-mono mb-1">{event.agent}</div>
                            <div className="text-sm text-slate-200">{event.action}</div>
                            <div className="text-xs text-slate-500 mt-1">{event.result}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 border border-dashed border-slate-800 rounded-xl bg-slate-900/30 p-12">
                <svg className="w-12 h-12 mb-4 text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                <p>Submit an incident to trace agent orchestration</p>
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  )
}
