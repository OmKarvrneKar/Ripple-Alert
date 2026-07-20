import sys

with open('e:/Application/RippleAlert/frontend/src/components/AlertManager.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Add state variables
old_state = """  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);"""

new_state = """  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [error, setError] = useState(null);"""

content = content.replace(old_state, new_state)

# Add test function
old_create = """  const handleCreateRule = async (e) => {"""

new_test = """  const handleTestRule = async (e) => {
    e.preventDefault();
    if (ruleType === 'price' && !symbol) return setError('Symbol is required');
    if (ruleType === 'portfolio_value' && (!threshold || !condition)) return setError('Condition and threshold are required for portfolio rules');
    
    setTesting(true);
    setError(null);
    setTestResult(null);
    
    const payload = {
      rule: {
        rule_type: ruleType,
        symbol: ruleType === 'price' ? symbol.toUpperCase() : undefined,
        condition,
        threshold: parseFloat(threshold),
        window_minutes: condition === 'percent_change_in_window' ? parseFloat(windowMinutes) : null
      },
      days: 7
    };
    
    try {
      const res = await fetch(`${API_URL}/rules/backtest`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      
      if (res.ok) {
        const data = await res.json();
        setTestResult(data);
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to backtest rule');
      }
    } catch (e) {
      console.error(e);
      setError('An error occurred during backtesting');
    } finally {
      setTesting(false);
    }
  };

  const handleCreateRule = async (e) => {"""

content = content.replace(old_create, new_test)

# Add UI
old_ui = """          <button 
            type="submit"
            disabled={creating}
            className="w-full bg-azure hover:bg-blue-600 text-white font-medium p-3 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50 mt-2"
          >
            {creating ? <Loader2 className="w-5 h-5 animate-spin" /> : <Plus className="w-5 h-5" />}
            Create Alert Rule
          </button>
        </form>
      </div>"""

new_ui = """          <div className="flex gap-3 mt-4">
            <button 
              type="button"
              onClick={handleTestRule}
              disabled={testing || creating}
              className="flex-1 bg-slate-deep border border-gray-700 hover:bg-gray-800 text-frost font-medium p-3 rounded-lg flex items-center justify-center transition-colors disabled:opacity-50"
            >
              {testing ? <Loader2 className="w-5 h-5 animate-spin mr-2" /> : null}
              Test Rule (7 Days)
            </button>
            <button 
              type="submit"
              disabled={creating || testing}
              className="flex-1 bg-azure hover:bg-blue-600 text-white font-medium p-3 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
            >
              {creating ? <Loader2 className="w-5 h-5 animate-spin" /> : <Plus className="w-5 h-5" />}
              Create Alert Live
            </button>
          </div>
        </form>
        
        {testResult && (
          <div className="mt-6 bg-midnight border border-gray-700 rounded-lg p-4">
            <h3 className="text-frost font-bold mb-2 flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-muted" /> Backtest Results (Last {testResult.days_analyzed} Days)
            </h3>
            <div className="flex gap-6 mb-4 text-sm text-steel">
              <div><span className="font-bold text-frost">{testResult.trigger_count}</span> Triggers</div>
              <div><span className="font-bold text-frost">{testResult.data_points.toLocaleString()}</span> Data points scanned</div>
            </div>
            {testResult.triggers && testResult.triggers.length > 0 ? (
              <div className="max-h-48 overflow-y-auto space-y-2 pr-2">
                {testResult.triggers.map((t, idx) => (
                  <div key={idx} className="flex justify-between items-center text-xs bg-slate-deep p-2 rounded border border-gray-800">
                    <span className="text-steel">{new Date(t.timestamp).toLocaleString()}</span>
                    <span className="font-mono text-frost">${t.price.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-steel italic">This rule would not have triggered in the historical window.</p>
            )}
          </div>
        )}
      </div>"""

content = content.replace(old_ui, new_ui)

import_old = "import { Trash2, AlertTriangle, Clock, Loader2, Plus, BellOff } from 'lucide-react';"
import_new = "import { Trash2, AlertTriangle, Clock, Loader2, Plus, BellOff, Activity } from 'lucide-react';"
content = content.replace(import_old, import_new)

with open('e:/Application/RippleAlert/frontend/src/components/AlertManager.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
