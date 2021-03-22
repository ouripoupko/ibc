import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ContractsComponent } from './contracts/contracts.component';
import { DeployComponent } from './deploy/deploy.component';
import { ContractDetailComponent } from './contract-detail/contract-detail.component';
import { PartnerComponent } from './partner/partner.component';

const routes: Routes = [
//  { path: '' },
  { path: ':agent/contracts', component: ContractsComponent },
  { path: ':agent/:name/details', component: ContractDetailComponent },
  { path: ':agent/deploy', component: DeployComponent },
  { path: ':agent/partner', component: PartnerComponent },
];


@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
