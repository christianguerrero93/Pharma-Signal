import "@/index.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Campaigns from "@/pages/Campaigns";
import CampaignBuilder from "@/pages/CampaignBuilder";
import CampaignDetail from "@/pages/CampaignDetail";
import AudienceScorer from "@/pages/AudienceScorer";
import PMPScorecard from "@/pages/PMPScorecard";
import DataCost from "@/pages/DataCost";
import GA4Engagement from "@/pages/GA4Engagement";
import ScriptLift from "@/pages/ScriptLift";
import RTBSimulator from "@/pages/RTBSimulator";
import LiveStream from "@/pages/LiveStream";
import AIRecommendations from "@/pages/AIRecommendations";
import VendorReports from "@/pages/VendorReports";
import MLRReview from "@/pages/MLRReview";
import DataUpload from "@/pages/DataUpload";
import { Toaster } from "@/components/ui/sonner";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="campaigns" element={<Campaigns />} />
            <Route path="campaigns/new" element={<CampaignBuilder />} />
            <Route path="campaigns/:id" element={<CampaignDetail />} />
            <Route path="audiences" element={<AudienceScorer />} />
            <Route path="pmp" element={<PMPScorecard />} />
            <Route path="data-cost" element={<DataCost />} />
            <Route path="ga4" element={<GA4Engagement />} />
            <Route path="script-lift" element={<ScriptLift />} />
            <Route path="rtb" element={<RTBSimulator />} />
            <Route path="live" element={<LiveStream />} />
            <Route path="ai" element={<AIRecommendations />} />
            <Route path="vendors" element={<VendorReports />} />
            <Route path="mlr" element={<MLRReview />} />
            <Route path="upload" element={<DataUpload />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster />
    </div>
  );
}

export default App;
