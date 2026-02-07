import { VulnerabilityScanner } from './components/VulnerabilityScanner';

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950">
      {/* Demo content to show the overlay works on top of existing content */}
      <div className="p-8">
        <h1 className="text-3xl font-bold text-white mb-4">Mayhem Monkey</h1>
        <p className="text-gray-400 mb-8">
          The vulnerability scanner overlay will appear on top of your existing application.
        </p>
        
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-6 max-w-4xl">
          <h2 className="text-xl font-semibold text-white mb-4">Code Example</h2>
          <pre className="bg-gray-950 p-4 rounded-lg text-gray-300 text-sm overflow-x-auto">
{`function authenticateUser(username, password) {
  const query = "SELECT * FROM users WHERE username = '" + username + "'";
  return database.execute(query);
}

function renderUserProfile(userData) {
  document.getElementById('profile').innerHTML = userData.bio;
}

function uploadFile(file) {
  saveToServer(file);
}`}
          </pre>
        </div>
      </div>

      <VulnerabilityScanner />
    </div>
  );
}