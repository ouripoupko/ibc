import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ContractsComponent } from './contracts/contracts.component';
import { DeployComponent } from './deploy/deploy.component';
import { ContractDetailComponent } from './contract-detail/contract-detail.component';

const routes: Routes = [
  { path: '', redirectTo: '/contracts', pathMatch: 'full' },
  { path: 'contracts', component: ContractsComponent },
  { path: 'detail/:name', component: ContractDetailComponent },
  { path: 'deploy', component: DeployComponent }
];


@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
