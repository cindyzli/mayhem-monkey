import { Shield } from 'lucide-react';

export default function App() {
  const openScanner = () => {
    window.electronAPI?.openScanner();
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      {/* Demo content */}
      <div className="p-8 flex flex-col items-center text-center">
        <h1 className="text-3xl font-bold text-white mb-4">Mayhem Monkey</h1>
        <p className="text-gray-400 mb-8">
          Click the button below to open the vulnerability scanner in a new always-on-top window.
        </p>

        <button
          onClick={openScanner}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors shadow-lg mb-8"
        >
          <Shield className="w-5 h-5" />
          Open Vulnerability Scanner
        </button>

        <div className="bg-gray-900 rounded-lg border border-gray-800 p-6 w-fit mt-8">
          <h2 className="text-xl font-semibold text-white mb-4 text-center">Vulnerability Code Example</h2>
          <pre className="bg-gray-950 p-4 rounded-lg text-gray-300 text-sm overflow-x-auto text-left">
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
    </div>
  );
}